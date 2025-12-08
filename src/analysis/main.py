import pandas as pd
import json
import argparse
import sys
from datetime import timedelta

def parse_arguments():
    parser = argparse.ArgumentParser(description='Analyze court case data from JSONL files.')
    parser.add_argument('file_path', nargs='?', default='/home/bob/github/tanas0/portfolio/court-cases/output/2024/05/01.json',
                        help='Path to the JSONL data file.')
    return parser.parse_args()

def extract_features(row):
    """
    Extracts all necessary features from a single row (record).
    Returns a pandas Series.
    """
    # 1. Basic Info
    try:
        disposition_text = row['disposition']['dispositionInfo']['dispositionText']
    except (KeyError, TypeError):
        disposition_text = None

    # 2. Demographics (Defendant)
    race, gender = None, None
    participants = row.get('caseParticipant', [])
    attorney_type = 'None/Private' # Default
    
    if isinstance(participants, list):
        for p in participants:
            if p.get('participantCode') == 'DEF':
                details = p.get('personalDetails', {})
                race = details.get('race')
                gender = details.get('gender')
                
                # Check for Public Defender in attorney details
                attorneys = p.get('attorneyDetails', [])
                if isinstance(attorneys, list):
                    for att in attorneys:
                        business_name = att.get('attorneyBusinessName', {}).get('businessName', '').upper()
                        official_cat = att.get('judicialOfficialCategoryText', '')
                        if 'PD' in business_name or 'PUBLIC DEFENDER' in business_name or official_cat == 'P':
                            attorney_type = 'Public Defender'
                            break
                break

    # 3. Dates & Time-to-Disposition
    offense_date = row.get('offenseDate')
    try:
        disposition_date = row['disposition']['dispositionInfo']['dispositionDate']
    except (KeyError, TypeError):
        disposition_date = None

    # 4. Sentencing (Calculate Net Active Sentence in Days)
    net_sentence_days = 0
    try:
        sent_info = row.get('sentencingInformation', {})
        sentence = sent_info.get('sentence') or {}
        suspended = sent_info.get('sentenceSuspended') or {}
        
        def to_days(d):
            return (d.get('years', 0) * 365) + (d.get('months', 0) * 30) + d.get('days', 0)
        
        total_days = to_days(sentence)
        suspended_days = to_days(suspended)
        net_sentence_days = max(0, total_days - suspended_days)
    except (AttributeError, TypeError):
        pass

    # 5. Financials
    total_fines = 0.0
    total_costs = 0.0
    try:
        fin_info = row.get('financialInformation', {})
        total_fines = float(fin_info.get('fines', {}).get('imposedAmount', {}).get('decimal', 0.0))
        total_costs = float(fin_info.get('costs', {}).get('amount', {}).get('decimal', 0.0))
    except (AttributeError, TypeError, ValueError):
        pass

    # 6. Hearing Complexity
    num_hearings = len(row.get('caseHearing', []) or [])

    return pd.Series({
        'dispositionText': disposition_text,
        'race': race,
        'gender': gender,
        'attorneyType': attorney_type,
        'offenseDate': offense_date,
        'dispositionDate': disposition_date,
        'netSentenceDays': net_sentence_days,
        'totalFines': total_fines,
        'totalCosts': total_costs,
        'numHearings': num_hearings
    })

def main():
    args = parse_arguments()
    
    print(f"Loading data from: {args.file_path}")
    
    try:
        # Load data directly into pandas
        df_raw = pd.read_json(args.file_path, lines=True)
    except ValueError as e:
        print(f"Error reading JSONL file: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"File not found: {args.file_path}")
        sys.exit(1)

    if df_raw.empty:
        print("Dataset is empty.")
        sys.exit(0)

    # Apply extractions
    print("Extracting features...")
    features_df = df_raw.apply(extract_features, axis=1)
    df = pd.concat([df_raw[['caseNumber', 'hearingDate', 'chargeDesc', 'codeSection', 'courtLevel']], features_df], axis=1)

    # Convert dates
    df['hearingDate'] = pd.to_datetime(df['hearingDate'], errors='coerce')
    df['offenseDate'] = pd.to_datetime(df['offenseDate'], errors='coerce')
    df['dispositionDate'] = pd.to_datetime(df['dispositionDate'], errors='coerce')
    
    # Calculate Time to Disposition
    df['daysToDisposition'] = (df['dispositionDate'] - df['offenseDate']).dt.days

    print("\n--- Data Info ---")
    print(df.info())

    # --- Insight 1: Top 10 Most Frequent Charge Code Sections ---
    print("\n--- Top 10 Most Frequent Code Sections ---")
    print(df['codeSection'].value_counts().nlargest(10).to_markdown())

    # --- Insight 2: Disposition Distribution ---
    print("\n--- Final Disposition Distribution (%) ---")
    print(df['dispositionText'].value_counts(normalize=True).mul(100).round(2).to_markdown(floatfmt=".2f"))

    # --- Insight 3: Charge vs. Outcome (Simple Crosstab) ---
    top_5_charges = df['codeSection'].value_counts().nlargest(5).index
    charge_outcome_crosstab = pd.crosstab(
        df[df['codeSection'].isin(top_5_charges)]['codeSection'], 
        df['dispositionText'], 
        normalize='index'
    ).mul(100).round(1)
    
    print("\n--- Charge Outcomes (Normalized by Charge) (%) ---")
    print(charge_outcome_crosstab.to_markdown(floatfmt=".1f"))

    # --- Insight 4: Disparity in Dismissal Rates ---
    df_demographics = df.dropna(subset=['race', 'gender', 'dispositionText'])
    dismissal_rates = df_demographics.groupby('race')['dispositionText'].apply(
        lambda x: (x == 'D').sum() / len(x)
    ).mul(100).round(2).sort_values(ascending=False)
    
    print("\n--- Dismissal Rate ('D') by Race (%) ---")
    print(dismissal_rates.to_markdown(floatfmt=".2f"))

    # --- NEW INSIGHTS ---

    # --- Insight 5: Sentencing Analysis (Net Active Sentence) ---
    # Filter for Guilty verdicts where there is a sentence
    df_guilty = df[df['dispositionText'].isin(['G', 'GA'])] # G=Guilty, GA=Guilty Absentia (common codes)
    if not df_guilty.empty:
        avg_sentence = df_guilty.groupby('codeSection')['netSentenceDays'].mean().nlargest(5)
        print("\n--- Top 5 Charges by Average Net Active Sentence (Days) ---")
        print(avg_sentence.to_markdown(floatfmt=".1f"))
    else:
        print("\n--- No Guilty verdicts found for Sentencing Analysis ---")

    # --- Insight 6: Time-to-Disposition Analysis ---
    avg_days = df['daysToDisposition'].mean()
    print(f"\n--- Average Time to Disposition: {avg_days:.1f} days ---")

    # --- Insight 7: Financial Impact Analysis ---
    df['totalFinancial'] = df['totalFines'] + df['totalCosts']
    avg_financial = df.groupby('codeSection')['totalFinancial'].mean().nlargest(5)
    print("\n--- Top 5 Charges by Average Financial Impact ($) ---")
    print(avg_financial.to_markdown(floatfmt=".2f"))

    # --- Insight 8: Legal Representation Analysis ---
    # Compare Dismissal Rate for Public Defender vs Others
    # Only consider cases where we could determine attorney type
    rep_dismissal = df.groupby('attorneyType')['dispositionText'].apply(
        lambda x: (x == 'D').sum() / len(x)
    ).mul(100).round(2)
    print("\n--- Dismissal Rate by Legal Representation (%) ---")
    print(rep_dismissal.to_markdown(floatfmt=".2f"))

    # --- Insight 9: Hearing Complexity Analysis ---
    avg_hearings = df['numHearings'].mean()
    print(f"\n--- Average Hearings per Case: {avg_hearings:.2f} ---")
    
    # Top 5 most complex cases (by hearings)
    print("\n--- Top 5 Cases by Number of Hearings ---")
    print(df[['caseNumber', 'numHearings', 'codeSection']].nlargest(5, 'numHearings').to_markdown(index=False))

if __name__ == "__main__":
    main()