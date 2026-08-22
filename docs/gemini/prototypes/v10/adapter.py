import pandas as pd
import json
import math

def load_v10(excel_path):
    xls = pd.ExcelFile(excel_path)
    
    # parse Overview for sessions
    df_overview = pd.read_excel(xls, 'Overview', header=1)
    
    sessions = []
    # Master Registry might be better for sessions since we want sessionUID* 
    df_master = pd.read_excel(xls, 'Master Registry', header=1)
    
    # We need to map unique sessions
    # The sessionUID is in `sessionUID*`, exp in `Exp`, date in `Date*`
    
    df_sessions = df_master[['sessionUID*', 'Exp', 'Date*', 'Time', 'Arrangement', 'annotationSet']].drop_duplicates(subset=['sessionUID*']).dropna(subset=['sessionUID*'])
    
    for _, row in df_sessions.iterrows():
        # format date as string
        date_str = str(row['Date*']).split(' ')[0] if pd.notnull(row['Date*']) else ""
        time_str = str(row['Time']) if pd.notnull(row['Time']) else None
        arrangement = str(row['Arrangement']) if pd.notnull(row['Arrangement']) else None
        ann_set = str(row['annotationSet']) if pd.notnull(row['annotationSet']) else None
        
        session = {
            "session_uid": str(row['sessionUID*']),
            "exp": str(int(row['Exp'])) if pd.notnull(row['Exp']) else str(row['Exp']),
            "date": date_str,
            "time": time_str,
            "name": None, # Name is not clearly in master registry, we can fetch from overview if needed
            "arrangement": arrangement,
            "annotation_set": ann_set
        }
        sessions.append(session)

    images = []
    for _, row in df_master.iterrows():
        if pd.isnull(row['Image UID']):
            continue
            
        img = {
            "image_uid": str(row['Image UID']),
            "session_uid": str(row['sessionUID*']),
            "image_number": int(row['Image #']),
            "original": str(row['Original']),
            "working_filename": str(row['Working filename']) if pd.notnull(row['Working filename']) else None,
            "exp": str(int(row['Exp'])) if pd.notnull(row['Exp']) else str(row['Exp']),
            "set": str(row['Set']),
            "media": str(row['Media']) if pd.notnull(row['Media']) else None,
            "condition": str(row['Condition']) if pd.notnull(row['Condition']) else None,
            "rep": int(row['Rep #']) if pd.notnull(row['Rep #']) else None,
            "arrangement": str(row['Arrangement']) if pd.notnull(row['Arrangement']) else None,
            "annotation_set": str(row['annotationSet']) if pd.notnull(row['annotationSet']) else None
        }
        images.append(img)
        
    project_model = {
        "contract_version": 1,
        "sessions": sessions,
        "images": images
    }
    
    return project_model


def extract_layouts(excel_path):
    xls = pd.ExcelFile(excel_path)
    df_ann = pd.read_excel(xls, 'Annotations', header=1)
    
    # 1. Parse Annotation Set Assignments
    assignments = df_ann[['annotationSet', 'Type', 'Profile', 'Order']].dropna(subset=['annotationSet', 'Type', 'Profile'])
    
    # 2. Parse Profiles
    df_strain = df_ann[['Strain profile', 'labels_strain', 'Pos']].copy()
    df_strain['Strain profile'] = df_strain['Strain profile'].ffill()
    df_strain = df_strain.dropna(subset=['labels_strain', 'Pos'])
    
    df_vertical = df_ann[['Vertical profile', 'labels_vertical', 'Pos.1']].copy()
    df_vertical['Vertical profile'] = df_vertical['Vertical profile'].ffill()
    df_vertical = df_vertical.dropna(subset=['labels_vertical', 'Pos.1'])
    
    layouts = {}
    
    grouped_assignments = assignments.groupby('annotationSet')
    for ann_set, group in grouped_assignments:
        strains = group[group['Type'] == 'strain']
        verticals = group[group['Type'] == 'vertical']
        
        if verticals.empty:
            continue
            
        vert_profile_name = verticals.iloc[0]['Profile']
        vert_labels_df = df_vertical[df_vertical['Vertical profile'] == vert_profile_name]
        
        vertical_labels = []
        for _, vrow in vert_labels_df.iterrows():
            # label can be a number or string
            val = vrow['labels_vertical']
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            vertical_labels.append({
                "pos": int(vrow['Pos.1']),
                "label": str(val)
            })
            
        grid_rows = len(vertical_labels)
        
        strain_bands = []
        max_cols = 0
        
        # Sort strains by order
        strains = strains.sort_values('Order')
        num_strain_bands = len(strains)
        
        row_chunks = grid_rows // num_strain_bands if num_strain_bands > 0 else grid_rows
        
        for idx, (_, srow) in enumerate(strains.iterrows()):
            strain_profile_name = srow['Profile']
            strain_labels_df = df_strain[df_strain['Strain profile'] == strain_profile_name]
            
            labels = []
            for _, lrow in strain_labels_df.iterrows():
                val = lrow['labels_strain']
                if isinstance(val, float) and val.is_integer():
                    val = int(val)
                labels.append({
                    "pos": int(lrow['Pos']),
                    "label": str(val)
                })
                
            if len(labels) > max_cols:
                max_cols = len(labels)
                
            order = int(srow['Order']) if pd.notnull(srow['Order']) else (idx + 1)
            
            # Simple row resolution
            row_start = (order - 1) * row_chunks + 1
            row_end = order * row_chunks
            
            strain_bands.append({
                "order": order,
                "profile": strain_profile_name,
                "row_start": row_start,
                "row_end": row_end,
                "labels": labels
            })
            
        layout = {
            "contract_version": 1,
            "layout_id": ann_set,
            "grid_rows": grid_rows,
            "grid_cols": max_cols,
            "vertical_labels": vertical_labels,
            "strain_bands": strain_bands
        }
        layouts[ann_set] = layout
        
    return layouts

if __name__ == "__main__":
    import sys
    path = "fixtures/v10/v10_sample_synthetic_sanitized.xlsx"
    pm = load_v10(path)
    print("ProjectModel parsed successfully. Images count:", len(pm["images"]))
    layouts = extract_layouts(path)
    print("Layouts parsed successfully. Layouts count:", len(layouts))
    for k, v in layouts.items():
        print(f"Layout {k}: grid={v['grid_rows']}x{v['grid_cols']} bands={len(v['strain_bands'])}")
