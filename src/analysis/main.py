import pandas as pd
import numpy as np
import argparse
import sys
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

# Import utility
from src.analysis.utils.data_loader import load_and_preprocess
import src.analysis.visualize as visualize


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Analyze court case data with advanced statistical methods."
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default="output/2024/05/01.json",
        help="Path to the JSONL data file.",
    )
    parser.add_argument(
        "--output-dir",
        default="output/plots",
        help="Directory to save the generated plots.",
    )
    return parser.parse_args()


def print_descriptive_stats(df, output_dir):
    print("\n" + "=" * 50)
    print("  DESCRIPTIVE STATISTICS  ")
    print("=" * 50)

    # --- 1. Central Tendency & Dispersion ---
    # Mathematical Concept: Median vs. Mean
    # Legal data (fines, sentences) is typically "Right-Skewed" (long tail of high values).
    # The Mean is sensitive to outliers (e.g., one life sentence pulls up the average significantly).
    # The Median (50th percentile) is robust and represents the "typical" defendant.
    # The IQR (Interquartile Range, 75th - 25th percentile) measures the spread of the middle 50% of data.

    columns_to_plot = [
        ("daysToDisposition", "Time to Disposition (Days)"),
        ("netSentenceDays", "Net Active Sentence (Days)"),
        ("totalFinancial", "Total Financial Impact ($)"),
    ]

    for col, name in columns_to_plot:
        data = df[col].dropna()
        if data.empty:
            continue

        mean_val = data.mean()
        median_val = data.median()
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        skew = data.skew()

        print(f"\n--- {name} ---")
        print(f"  Mean:   {mean_val:8.2f} (Sensitive to outliers)")
        print(f"  Median: {median_val:8.2f} (Robust measure of central tendency)")
        print(f"  IQR:    {iqr:8.2f} (Spread of middle 50%)")
        print(f"  Skew:   {skew:8.2f} (Positive = Right-skewed/Long tail)")

    # Generate Plots
    visualize.plot_distributions(df, columns_to_plot, output_dir)


def perform_hypothesis_tests(df, output_dir):
    print("\n" + "=" * 50)
    print("  STATISTICAL HYPOTHESIS TESTING")
    print("=" * 50)

    # --- Test 1: Chi-Square Test of Independence (Race vs. Dismissal) ---
    # Mathematical Concept: Chi-Square Test (χ²)
    # Used to determine if there is a significant association between two categorical variables.
    # Null Hypothesis (H0): Race and Dismissal Rate are independent (no bias).
    # Alternative Hypothesis (H1): Race and Dismissal Rate are associated.
    # p-value < 0.05 typically indicates we reject H0 (statistically significant difference).

    print("\n[Test 1] Association between Race and Dismissal ('D')")

    # Create binary outcome: Dismissed (True) vs Not Dismissed (False)
    df["is_dismissed"] = df["dispositionText"] == "D"

    # Filter for major demographic groups to ensure sufficient sample size
    # Small sample sizes violate Chi-Square assumptions (expected count < 5).
    top_races = df["race"].value_counts().nlargest(3).index  # TODO Filter by count > 5
    df_race = df[df["race"].isin(top_races)].dropna(subset=["race"])

    contingency_table = pd.crosstab(df_race["race"], df_race["is_dismissed"])
    chi2, p, dof, expected = stats.chi2_contingency(contingency_table)

    print(f"  Groups compared: {list(top_races)}")
    print(f"  Chi-Square Statistic: {chi2:.4f}")
    print(f"  p-value: {p:.4e}")
    if p < 0.05:
        print("  >> RESULT: Statistically Significant Association detected.")
    else:
        print(
            "  >> RESULT: No significant association detected (could be due to chance)."
        )

    # Plot Association
    visualize.plot_categorical_association(df_race, "race", "is_dismissed", output_dir)

    # --- Test 2: Mann-Whitney U Test (Attorney Type vs. Sentence Length) ---
    # Mathematical Concept: Mann-Whitney U Test
    # A non-parametric test to compare differences between two independent groups.
    # We use this instead of a T-Test because sentence data is not normally distributed (skewed).
    # H0: The distributions of sentence lengths are the same for Public Defenders vs Private Attorneys.

    print(
        "\n[Test 2] Impact of Representation on Sentence Length (Public Defender vs Private)"
    )

    df_sent = df[df["netSentenceDays"] > 0].dropna(subset=["attorneyType"])
    pd_sentences = df_sent[df_sent["attorneyType"] == "Public Defender"][
        "netSentenceDays"
    ]
    priv_sentences = df_sent[df_sent["attorneyType"] != "Public Defender"][
        "netSentenceDays"
    ]

    if len(pd_sentences) > 5 and len(priv_sentences) > 5:
        u_stat, p_val = stats.mannwhitneyu(
            pd_sentences, priv_sentences, alternative="two-sided"
        )

        print(f"  Median Sentence (Public Defender): {pd_sentences.median():.1f} days")
        print(
            f"  Median Sentence (Private/Other):   {priv_sentences.median():.1f} days"
        )
        print(f"  p-value: {p_val:.4e}")
        if p_val < 0.05:
            print(
                "  >> RESULT: Statistically Significant Difference in sentence lengths."
            )
        else:
            print("  >> RESULT: No significant difference found.")
    else:
        print("  >> Insufficient data for Mann-Whitney test.")


def perform_multivariate_analysis(df, output_dir):
    print("\n" + "=" * 50)
    print("  MULTIVARIATE ANALYSIS (Logistic Regression)")
    print("=" * 50)

    # Mathematical Concept: Logistic Regression
    # Simple correlation (like Test 1) can be misleading due to "Confounding Variables".
    # Example: Group A might have lower dismissal rates not because of bias, but because they face more serious charges.
    # Logistic Regression allows us to estimate the probability of an event (Dismissal) based on multiple independent variables (X).
    # Equation: ln(P / (1-P)) = β0 + β1*Race + β2*Gender + β3*Attorney + ...
    # The coefficients (β) - or rather their exponentiated form (Odds Ratios) - tell us the effect of one variable
    # *holding all other variables constant*.

    print("\n[Model] Predicting Probability of Dismissal")

    # 1. Prepare Data
    features = ["race", "gender", "attorneyType", "codeSection"]
    target = "is_dismissed"

    # Filter data
    model_df = df[features + [target]].dropna()

    # Keep only top categories to avoid "Curse of Dimensionality" (too many sparse columns)
    # Group rare categories into "Other"
    for col in ["race", "codeSection"]:
        top_n = model_df[col].value_counts().nlargest(5).index
        model_df[col] = model_df[col].apply(lambda x: x if x in top_n else "Other")

    X = model_df[features]
    y = model_df[target]

    if len(y) < 50:
        print("  >> Insufficient data for reliable regression model.")
        return

    # 2. Pipeline: One-Hot Encoding -> Logistic Regression
    # We use One-Hot Encoding to convert categorical text data into binary (0/1) columns.
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), features)
        ]
    )

    clf = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=1000, solver="lbfgs")),
        ]
    )

    clf.fit(X, y)

    # 3. Interpret Results (Odds Ratios)
    # Odds Ratio (OR) = exp(coefficient)
    # OR > 1: Increases odds of dismissal
    # OR < 1: Decreases odds of dismissal
    # OR = 1: No effect

    feature_names = clf.named_steps["preprocessor"].get_feature_names_out()
    coefficients = clf.named_steps["classifier"].coef_[0]

    results = pd.DataFrame(
        {"Feature": feature_names, "Odds Ratio": np.exp(coefficients)}
    )
    results = results.sort_values("Odds Ratio", ascending=False)

    print("\n  --- Independent Effects on Dismissal Odds (Odds Ratio) ---")
    print(
        "  (Values > 1.0 indicate HIGHER chance of dismissal, < 1.0 indicate LOWER chance)"
    )
    print("  (Controlled for all other factors in the table)")
    print("-" * 70)
    print(results.to_markdown(index=False, floatfmt=".2f"))

    # Plot Odds Ratios
    visualize.plot_odds_ratios(results, output_dir)


def main():
    args = parse_arguments()

    # 1. Load (from utility)
    df = load_and_preprocess(args.file_path)

    # Set style
    visualize.setup_style()

    # 2. Descriptive Stats (Robust)
    print_descriptive_stats(df, args.output_dir)

    # 3. Hypothesis Testing
    perform_hypothesis_tests(df, args.output_dir)

    # 4. Multivariate Analysis
    perform_multivariate_analysis(df, args.output_dir)


if __name__ == "__main__":
    main()
