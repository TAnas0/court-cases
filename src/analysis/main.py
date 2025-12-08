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

def parse_arguments():
    parser = argparse.ArgumentParser(description='Analyze court case data with advanced statistical methods.')
    parser.add_argument('file_path', nargs='?', default='/home/bob/github/tanas0/portfolio/court-cases/output/2024/05/01.json',
                        help='Path to the JSONL data file.')
    return parser.parse_args()

def load_and_preprocess(file_path):
    """
    Loads JSONL data and performs vectorized feature extraction.
    
    Vectorization replaces slow row-by-row loops with optimized C-level array operations
    provided by Pandas and NumPy. This significantly improves performance on large datasets.
    """
    print(f"Loading data from: {file_path}")
    try:
        df = pd.read_json(file_path, lines=True)
    except ValueError as e:
        print(f"Error reading JSONL file: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        sys.exit(1)

    if df.empty:
        print("Dataset is empty.")
        sys.exit(0)

    print("Preprocessing and extracting features (Vectorized)...")

    # --- 1. Extract Disposition ---
    # We use .str accessor to drill down into the JSON structure efficiently
    df['dispositionText'] = df['disposition'].apply(lambda x: x.get('dispositionInfo', {}).get('dispositionText') if isinstance(x, dict) else None)
    df['dispositionDate'] = pd.to_datetime(df['disposition'].apply(lambda x: x.get('dispositionInfo', {}).get('dispositionDate') if isinstance(x, dict) else None), errors='coerce')
    df['offenseDate'] = pd.to_datetime(df['offenseDate'], errors='coerce')

    # --- 2. Calculate Time-to-Disposition ---
    # Mathematical Note: We calculate the difference in days. 
    # We filter out negative values which represent data errors (disposition before offense).
    df['daysToDisposition'] = (df['dispositionDate'] - df['offenseDate']).dt.days
    df.loc[df['daysToDisposition'] < 0, 'daysToDisposition'] = np.nan

    # --- 3. Extract Defendant Demographics & Attorney Type ---
    # Strategy: Explode the 'caseParticipant' list to have one row per participant,
    # filter for 'DEF' (Defendant), then merge back. This avoids row-by-row iteration.
    
    # Create a temporary dataframe of participants
    df_parts = df[['caseNumber', 'caseParticipant']].explode('caseParticipant')
    
    # Normalize the dictionary in 'caseParticipant' column
    # We use pd.json_normalize but since it expects a list, we might need a custom apply if structure varies.
    # For speed on complex nested structures, apply is often acceptable if the inner operation is simple.
    
    def extract_part_details(p):
        if not isinstance(p, dict): return pd.Series()
        code = p.get('participantCode')
        if code != 'DEF': return pd.Series()
        
        details = p.get('personalDetails', {})
        race = details.get('race')
        gender = details.get('gender')
        
        # Attorney Heuristic
        att_type = 'Private/None'
        attorneys = p.get('attorneyDetails', [])
        if isinstance(attorneys, list):
            for att in attorneys:
                b_name = att.get('attorneyBusinessName', {}).get('businessName', '').upper()
                off_cat = att.get('judicialOfficialCategoryText', '')
                if 'PD' in b_name or 'PUBLIC DEFENDER' in b_name or off_cat == 'P':
                    att_type = 'Public Defender'
                    break
        
        return pd.Series({'race': race, 'gender': gender, 'attorneyType': att_type})

    # Note: For extremely large datasets, we would optimize this further. 
    # For now, applying to the exploded view is faster than the original nested loop.
    part_features = df_parts['caseParticipant'].apply(extract_part_details)
    part_features = part_features.dropna(how='all') # Drop non-DEF rows
    
    # Join back to original DF. We use the index since explode preserves it.
    # We group by index and take the first defendant found (usually only one per case)
    part_features = part_features.groupby(part_features.index).first()
    
    df = df.join(part_features)

    # --- 4. Financials ---
    # Vectorized extraction using apply with safe get
    def get_fin(row):
        try:
            fin = row.get('financialInformation', {})
            fines = float(fin.get('fines', {}).get('imposedAmount', {}).get('decimal', 0.0))
            costs = float(fin.get('costs', {}).get('amount', {}).get('decimal', 0.0))
            return fines + costs
        except:
            return 0.0
            
    df['totalFinancial'] = df.apply(get_fin, axis=1)

    # --- 5. Net Sentence Days ---
    def get_sentence(row):
        try:
            sent_info = row.get('sentencingInformation', {})
            if not sent_info: return 0
            
            def to_days(d):
                if not isinstance(d, dict): return 0
                return (d.get('years', 0) * 365) + (d.get('months', 0) * 30) + d.get('days', 0)

            total = to_days(sent_info.get('sentence'))
            suspended = to_days(sent_info.get('sentenceSuspended'))
            return max(0, total - suspended)
        except:
            return 0

    df['netSentenceDays'] = df.apply(get_sentence, axis=1)

    return df

def print_descriptive_stats(df):
    print("\n" + "="*50)
    print("  DESCRIPTIVE STATISTICS (Robust Measures)")
    print("="*50)
    
    # --- 1. Central Tendency & Dispersion ---
    # Mathematical Concept: Median vs. Mean
    # Legal data (fines, sentences) is typically "Right-Skewed" (long tail of high values).
    # The Mean is sensitive to outliers (e.g., one life sentence pulls up the average significantly).
    # The Median (50th percentile) is robust and represents the "typical" defendant.
    # The IQR (Interquartile Range, 75th - 25th percentile) measures the spread of the middle 50% of data.
    
    for col, name in [('daysToDisposition', 'Time to Disposition (Days)'), 
                      ('netSentenceDays', 'Net Active Sentence (Days)'), 
                      ('totalFinancial', 'Total Financial Impact ($)')]:
        data = df[col].dropna()
        if data.empty: continue
        
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

def perform_hypothesis_tests(df):
    print("\n" + "="*50)
    print("  STATISTICAL HYPOTHESIS TESTING")
    print("="*50)
    
    # --- Test 1: Chi-Square Test of Independence (Race vs. Dismissal) ---
    # Mathematical Concept: Chi-Square Test (χ²)
    # Used to determine if there is a significant association between two categorical variables.
    # Null Hypothesis (H0): Race and Dismissal Rate are independent (no bias).
    # Alternative Hypothesis (H1): Race and Dismissal Rate are associated.
    # p-value < 0.05 typically indicates we reject H0 (statistically significant difference).
    
    print("\n[Test 1] Association between Race and Dismissal ('D')")
    
    # Create binary outcome: Dismissed (True) vs Not Dismissed (False)
    df['is_dismissed'] = df['dispositionText'] == 'D'
    
    # Filter for major demographic groups to ensure sufficient sample size
    # Small sample sizes violate Chi-Square assumptions (expected count < 5).
    top_races = df['race'].value_counts().nlargest(3).index
    df_race = df[df['race'].isin(top_races)].dropna(subset=['race'])
    
    contingency_table = pd.crosstab(df_race['race'], df_race['is_dismissed'])
    chi2, p, dof, expected = stats.chi2_contingency(contingency_table)
    
    print(f"  Groups compared: {list(top_races)}")
    print(f"  Chi-Square Statistic: {chi2:.4f}")
    print(f"  p-value: {p:.4e}")
    if p < 0.05:
        print("  >> RESULT: Statistically Significant Association detected.")
    else:
        print("  >> RESULT: No significant association detected (could be due to chance).")

    # --- Test 2: Mann-Whitney U Test (Attorney Type vs. Sentence Length) ---
    # Mathematical Concept: Mann-Whitney U Test
    # A non-parametric test to compare differences between two independent groups.
    # We use this instead of a T-Test because sentence data is not normally distributed (skewed).
    # H0: The distributions of sentence lengths are the same for Public Defenders vs Private Attorneys.
    
    print("\n[Test 2] Impact of Representation on Sentence Length (Public Defender vs Private)")
    
    df_sent = df[df['netSentenceDays'] > 0].dropna(subset=['attorneyType'])
    pd_sentences = df_sent[df_sent['attorneyType'] == 'Public Defender']['netSentenceDays']
    priv_sentences = df_sent[df_sent['attorneyType'] != 'Public Defender']['netSentenceDays']
    
    if len(pd_sentences) > 5 and len(priv_sentences) > 5:
        u_stat, p_val = stats.mannwhitneyu(pd_sentences, priv_sentences, alternative='two-sided')
        
        print(f"  Median Sentence (Public Defender): {pd_sentences.median():.1f} days")
        print(f"  Median Sentence (Private/Other):   {priv_sentences.median():.1f} days")
        print(f"  p-value: {p_val:.4e}")
        if p_val < 0.05:
            print("  >> RESULT: Statistically Significant Difference in sentence lengths.")
        else:
            print("  >> RESULT: No significant difference found.")
    else:
        print("  >> Insufficient data for Mann-Whitney test.")

def perform_multivariate_analysis(df):
    print("\n" + "="*50)
    print("  MULTIVARIATE ANALYSIS (Logistic Regression)")
    print("="*50)
    
    # Mathematical Concept: Logistic Regression
    # Simple correlation (like Test 1) can be misleading due to "Confounding Variables".
    # Example: Group A might have lower dismissal rates not because of bias, but because they face more serious charges.
    # Logistic Regression allows us to estimate the probability of an event (Dismissal) based on multiple independent variables (X).
    # Equation: ln(P / (1-P)) = β0 + β1*Race + β2*Gender + β3*Attorney + ...
    # The coefficients (β) - or rather their exponentiated form (Odds Ratios) - tell us the effect of one variable
    # *holding all other variables constant*.
    
    print("\n[Model] Predicting Probability of Dismissal")
    
    # 1. Prepare Data
    features = ['race', 'gender', 'attorneyType', 'codeSection']
    target = 'is_dismissed'
    
    # Filter data
    model_df = df[features + [target]].dropna()
    
    # Keep only top categories to avoid "Curse of Dimensionality" (too many sparse columns)
    # Group rare categories into "Other"
    for col in ['race', 'codeSection']:
        top_n = model_df[col].value_counts().nlargest(5).index
        model_df[col] = model_df[col].apply(lambda x: x if x in top_n else 'Other')

    X = model_df[features]
    y = model_df[target]
    
    if len(y) < 50:
        print("  >> Insufficient data for reliable regression model.")
        return

    # 2. Pipeline: One-Hot Encoding -> Logistic Regression
    # We use One-Hot Encoding to convert categorical text data into binary (0/1) columns.
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', drop='first'), features)
        ])
    
    clf = Pipeline(steps=[('preprocessor', preprocessor),
                          ('classifier', LogisticRegression(max_iter=1000, solver='lbfgs'))])
    
    clf.fit(X, y)
    
    # 3. Interpret Results (Odds Ratios)
    # Odds Ratio (OR) = exp(coefficient)
    # OR > 1: Increases odds of dismissal
    # OR < 1: Decreases odds of dismissal
    # OR = 1: No effect
    
    feature_names = clf.named_steps['preprocessor'].get_feature_names_out()
    coefficients = clf.named_steps['classifier'].coef_[0]
    
    results = pd.DataFrame({'Feature': feature_names, 'Odds Ratio': np.exp(coefficients)})
    results = results.sort_values('Odds Ratio', ascending=False)
    
    print("\n  --- Independent Effects on Dismissal Odds (Odds Ratio) ---")
    print("  (Values > 1.0 indicate HIGHER chance of dismissal, < 1.0 indicate LOWER chance)")
    print("  (Controlled for all other factors in the table)")
    print("-" * 70)
    print(results.to_markdown(index=False, floatfmt=".2f"))

def main():
    args = parse_arguments()
    
    # 1. Load
    df = load_and_preprocess(args.file_path)
    
    # 2. Descriptive Stats (Robust)
    print_descriptive_stats(df)
    
    # 3. Hypothesis Testing
    perform_hypothesis_tests(df)
    
    # 4. Multivariate Analysis
    perform_multivariate_analysis(df)

if __name__ == "__main__":
    main()