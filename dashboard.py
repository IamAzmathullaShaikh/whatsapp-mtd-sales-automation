import os
import pandas as pd
from openpyxl import load_workbook
from openpyxl.chart import BarChart, Reference

def export_territory_dashboard(dashboard_rows, file_date_str, mtd_cols):
    """Compiles the complete management workbook, leaderboards, and native charts."""
    dashboard_path = f"exports/territory_intelligence_dashboard_{file_date_str}.xlsx"
    os.makedirs("exports", exist_ok=True)
    
    df_main = pd.DataFrame(dashboard_rows)
    df_main = df_main.sort_values(by="Achievement %", ascending=True)
    
    # Write to Excel via specialized engine writer
    with pd.ExcelWriter(dashboard_path, engine='openpyxl') as writer:
        df_main.to_excel(writer, sheet_name="Territory Summary", index=False)
        
        # Build Segmented Brand Leaderboards
        for brand in mtd_cols:
            clean_name = brand.replace(".1", "")
            tgt_lbl, act_lbl = f"{clean_name} Target", f"{clean_name} MTD"
            
            if tgt_lbl in df_main.columns and act_lbl in df_main.columns:
                # Isolate active rows and establish rankings
                brand_df = df_main[["Party Name", tgt_lbl, act_lbl, "Achievement %"]].copy()
                brand_df = brand_df.sort_values(by=act_lbl, ascending=False)
                
                # Split Leaderboards
                top_10 = brand_df.head(10)
                bottom_10 = brand_df.tail(10).sort_values(by=act_lbl, ascending=True)
                
                start_row = 0
                top_10.to_excel(writer, sheet_name=f"{clean_name} Leaderboard", startrow=start_row, index=False)
                bottom_10.to_excel(writer, sheet_name=f"{clean_name} Leaderboard", startrow=start_row + 15, index=False)
                
    # inject Native openpyxl Data Charts onto the primary spreadsheet view
    wb = load_workbook(dashboard_path)
    ws = wb["Territory Summary"]
    
    chart = BarChart()
    chart.type = "col"
    chart.style = 10
    chart.title = "Target vs Actual Performance by Distributor"
    chart.y_axis.title = "Cases Volume"
    chart.x_axis.title = "Distributors"
    
    # References matching structured data shapes (Columns C and D represent Targets/Actuals)
    data = Reference(ws, min_col=3, min_row=1, max_col=4, max_row=len(dashboard_rows) + 1)
    cats = Reference(ws, min_col=1, min_row=2, max_row=len(dashboard_rows) + 1)
    
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    ws.add_chart(chart, "K2")
    wb.save(dashboard_path)
    print(f"📊 Dashboard compiled cleanly with data charts: {dashboard_path}")
