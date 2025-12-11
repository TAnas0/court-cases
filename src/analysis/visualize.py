import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
import numpy as np

def setup_style():
    """Sets a simple and professional plotting style."""
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['axes.labelsize'] = 14
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12
    plt.rcParams['legend.fontsize'] = 12
    plt.rcParams['figure.dpi'] = 100

def ensure_output_dir(output_dir):
    """Ensures the output directory exists."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

def plot_distributions(df, columns, output_dir):
    """
    Plots histograms and boxplots for numerical variables.
    
    Args:
        df (pd.DataFrame): The dataframe containing the data.
        columns (list of tuples): List of (column_name, display_name) tuples.
        output_dir (str): Directory to save the plots.
    """
    ensure_output_dir(output_dir)
    
    for col, name in columns:
        data = df[col].dropna()
        if data.empty:
            continue

        # Create a figure with two subplots: Histogram and Boxplot
        fig, (ax_box, ax_hist) = plt.subplots(2, 1, sharex=True, 
                                              gridspec_kw={"height_ratios": (.15, .85)}, 
                                              figsize=(10, 8))
        
        # Boxplot
        sns.boxplot(x=data, ax=ax_box, color="#4c72b0")
        ax_box.set(xlabel='')
        ax_box.set_title(f'Distribution of {name}', pad=20)
        
        # Histogram
        sns.histplot(data, ax=ax_hist, kde=True, color="#4c72b0", edgecolor="white")
        ax_hist.set_xlabel(name)
        ax_hist.set_ylabel('Frequency')
        
        # Add mean and median lines to histogram
        mean_val = data.mean()
        median_val = data.median()
        ax_hist.axvline(mean_val, color='r', linestyle='--', label=f'Mean: {mean_val:.2f}')
        ax_hist.axvline(median_val, color='g', linestyle='-', label=f'Median: {median_val:.2f}')
        ax_hist.legend()

        plt.tight_layout()
        filename = f"dist_{col}.png"
        plt.savefig(os.path.join(output_dir, filename))
        plt.close()
        print(f"Saved distribution plot: {filename}")

def plot_categorical_association(df, col1, col2, output_dir):
    """
    Plots a stacked bar chart for categorical associations.
    
    Args:
        df (pd.DataFrame): The dataframe.
        col1 (str): The independent categorical variable (e.g., 'race').
        col2 (str): The dependent binary/categorical variable (e.g., 'is_dismissed').
        output_dir (str): Directory to save the plot.
    """
    ensure_output_dir(output_dir)
    
    # Calculate proportions
    cross_tab = pd.crosstab(df[col1], df[col2], normalize='index') * 100
    
    # Sort by one of the categories for better readability (e.g., True for dismissal)
    if True in cross_tab.columns:
        cross_tab = cross_tab.sort_values(by=True, ascending=True)
    
    ax = cross_tab.plot(kind='barh', stacked=True, figsize=(10, 6), colormap='RdBu')
    
    plt.title(f'Association between {col1.capitalize()} and {col2}')
    plt.xlabel('Percentage (%)')
    plt.ylabel(col1.capitalize())
    plt.legend(title=col2, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    filename = f"association_{col1}_{col2}.png"
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()
    print(f"Saved association plot: {filename}")

def plot_group_comparison(df, group_col, value_col, output_dir):
    """
    Plots boxplots to compare a numerical variable across groups.
    
    Args:
        df (pd.DataFrame): The dataframe.
        group_col (str): The categorical grouping variable.
        value_col (str): The numerical variable.
        output_dir (str): Directory to save the plot.
    """
    ensure_output_dir(output_dir)
    
    plt.figure(figsize=(10, 6))
    sns.boxplot(x=group_col, y=value_col, data=df, palette="Set2")
    
    plt.title(f'{value_col} by {group_col}')
    plt.xlabel(group_col)
    plt.ylabel(value_col)
    plt.tight_layout()
    
    filename = f"comparison_{group_col}_{value_col}.png"
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()
    print(f"Saved comparison plot: {filename}")

def plot_odds_ratios(results_df, output_dir):
    """
    Plots odds ratios from logistic regression.
    
    Args:
        results_df (pd.DataFrame): DataFrame containing 'Feature' and 'Odds Ratio'.
        output_dir (str): Directory to save the plot.
    """
    ensure_output_dir(output_dir)
    
    plt.figure(figsize=(10, len(results_df) * 0.5 + 2))
    
    # Color code: Red for > 1 (Higher Risk), Blue for < 1 (Lower Risk)
    colors = ['#d62728' if x > 1 else '#1f77b4' for x in results_df['Odds Ratio']]
    
    sns.barplot(x='Odds Ratio', y='Feature', data=results_df, palette=colors, hue='Feature', legend=False)
    
    plt.axvline(x=1, color='black', linestyle='--', linewidth=1)
    plt.title('Odds Ratios for Dismissal (Logistic Regression)')
    plt.xlabel('Odds Ratio (log scale)')
    plt.xscale('log') # Log scale is often better for odds ratios
    plt.tight_layout()
    
    filename = "odds_ratios.png"
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()
    print(f"Saved odds ratio plot: {filename}")
