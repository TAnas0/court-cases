import pandas as pd
import numpy as np
import sys

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
