import pandas as pd

# Define paths for the datasets
datasets = {
    "rice_wheat_yield": r"C:\Users\dheer\Dropbox\project-samarth\Dataset\All India Level Yield of Rice and Wheat from 2014-15 to 2019-20 (From Ministry of Agriculture and Farmers Welfare).csv",
    "crop_production_cost": r"C:\Users\dheer\Dropbox\project-samarth\Dataset\Crop-wise Details of Production and Projected Demand under Pradhan Mantri Annadata Aay SanraksHan Abhiyan (PM-AASHA) from 2016-17 to 2021-22.csv",
    "air_quality_index": r"C:\Users\dheer\Dropbox\project-samarth\Dataset\Real time Air Quality Index from various locations.csv",
    "temp_series": r"C:\Users\dheer\Dropbox\project-samarth\Dataset\Seasonal and Annual MinMax Temp Series - India from 1901 to 2017.csv",
    "production_cost": r"C:\Users\dheer\Dropbox\project-samarth\Dataset\State-wise and Crop-wise Cost of Production (C2) for Important Crops from 2013-14 to 2017-18 (From Ministry of Agriculture and Farmers Welfare).csv",
    "climate_risk": r"C:\Users\dheer\Dropbox\project-samarth\Dataset\Year-wise Climate Risk Index Rank (India) from 2010 to 2021.csv"
}

# Function to load all datasets
def load_datasets():
    # Load each dataset into a dictionary of DataFrames
    dataframes = {}
    
    for name, path in datasets.items():
        try:
            print(f"Loading {name} dataset...")
            dataframes[name] = pd.read_csv(path)
        except Exception as e:
            print(f"Error loading {name}: {e}")
    
    return dataframes

# Function to preview the datasets
def preview_datasets(dataframes):
    for name, df in dataframes.items():
        print(f"\nPreview of {name} dataset:")
        print(df.head())  # Print the first 5 rows of each dataset

# Main function
if __name__ == "__main__":
    # Load datasets
    dataframes = load_datasets()
    
    # Preview datasets
    preview_datasets(dataframes)
