import folium
import pandas as pd
import requests
import time

# Your Mapbox access token
MAPBOX_TOKEN = 'pk.eyJ1IjoiZmxhbWIyMiIsImEiOiJjbWx0cXJzbGwwMzNsM2xwbmZqaWw2Zjk3In0.Lo4lEcg-rbCpdEAbAzyh2w'

# Custom Mapbox style ID
MAPBOX_STYLE = 'flamb22/cmm0wq4vu007601qz9f18a30a'

# Mapbox tile URL for Folium
tiles = f'https://api.mapbox.com/styles/v1/{MAPBOX_STYLE}/tiles/{{z}}/{{x}}/{{y}}?access_token={MAPBOX_TOKEN}'

# Manual coordinate corrections for known locations
MANUAL_COORDINATES = {
    'Oceanside Pier': (33.1941, -117.3798),  # Exact pier coordinates
    'Sea Lion Island': (33.1955, -117.3823),  # Near the harbor entrance
    'Harbor Beach': (33.2098, -117.3872),  # North beach by harbor
    'Oceanside Harbor': (33.2103, -117.3946),  # Harbor entrance
}

# Function to geocode an address using Mapbox Geocoding API
def geocode_address(address):
    """
    Convert an address to latitude/longitude coordinates using Mapbox Geocoding API
    """
    # Mapbox Geocoding API endpoint
    geocode_url = f'https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(address)}.json'
    
    params = {
        'access_token': MAPBOX_TOKEN,
        'limit': 1  # Only return the top result
    }
    
    try:
        response = requests.get(geocode_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['features']:
            # Extract longitude and latitude from the first result
            coordinates = data['features'][0]['center']
            lon, lat = coordinates
            return lat, lon
        else:
            print(f"❌ Could not geocode: {address}")
            return None, None
    except Exception as e:
        print(f"❌ Error geocoding {address}: {e}")
        return None, None

# Function to get marker color based on location type
def get_marker_color(location_type):
    """
    Return different colors for different location types
    """
    color_map = {
        'food': 'pink',
        'restaurant': 'pink',
        'beach': 'lightblue',
        'landmark': 'orange',
        'resort': 'beige',
    }
    return color_map.get(location_type.lower(), 'gray')

# Function to get marker icon based on location type
def get_marker_icon(location_type):
    """
    Return different icons for different location types
    """
    icon_map = {
        'food': 'cutlery',
        'restaurant': 'cutlery',
        'beach': 'water',  # Wave-like water icon
        'landmark': 'star',  # Star icon for landmarks
        'resort': 'bed',
        'park': 'tree',
        'cultural': 'university',
        'shopping': 'shopping-cart',
        'other': 'info-sign'
    }
    return icon_map.get(location_type.lower(), 'info-sign')

# Function to create popup HTML with image
def create_popup_html(name, description, image_path):
    """
    Create HTML for interactive popup with image
    """
    html = f"""
    <div style="width: 300px; font-family: Arial, sans-serif;">
        <h3 style="color: #4d1979; margin-bottom: 10px;">{name}</h3>
        <img src="{image_path}" style="width: 100%; height: auto; border-radius: 8px; margin-bottom: 10px;" alt="{name}">
        <p style="font-size: 14px; line-height: 1.6; color: #333;">{description}</p>
    </div>
    """
    return html

# Main function to create the map
def create_hometown_map(csv_file='Hometown Map Data.csv', output_file='hometown_map.html'):
    """
    Read CSV, geocode addresses, and create an interactive Folium map
    """
    print("📍 Reading CSV file...")
    # Read the CSV file
    df = pd.read_csv(csv_file)
    
    print(f"✅ Found {len(df)} locations")
    
    # Add latitude and longitude columns if they don't exist
    if 'LATITUDE' not in df.columns:
        df['LATITUDE'] = None
    if 'LONGITUDE' not in df.columns:
        df['LONGITUDE'] = None
    
    # Geocode addresses that don't have coordinates
    print("\n🌍 Geocoding addresses...")
    for idx, row in df.iterrows():
        # Check if we have manual coordinates for this location
        if row['NAME'] in MANUAL_COORDINATES:
            lat, lon = MANUAL_COORDINATES[row['NAME']]
            df.at[idx, 'LATITUDE'] = lat
            df.at[idx, 'LONGITUDE'] = lon
            print(f"  ✓ Using manual coordinates for: {row['NAME']}")
        # Check if coordinates are already in the CSV
        elif pd.isna(row.get('LATITUDE')) or pd.isna(row.get('LONGITUDE')):
            print(f"  → Geocoding: {row['NAME']}")
            lat, lon = geocode_address(row['ADDRESS'])
            df.at[idx, 'LATITUDE'] = lat
            df.at[idx, 'LONGITUDE'] = lon
            time.sleep(0.5)  # Be nice to the API - rate limiting
    
    # Calculate center of map (average of all coordinates)
    center_lat = df['LATITUDE'].mean()
    center_lon = df['LONGITUDE'].mean()
    
    print(f"\n🗺️  Creating map centered at: ({center_lat:.4f}, {center_lon:.4f})")
    
    # Create the Folium map with custom Mapbox basemap
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles=tiles,
        attr='Mapbox'
    )
    
    # Add markers for each location
    print("\n📌 Adding markers to map...")
    for idx, row in df.iterrows():
        if pd.notna(row['LATITUDE']) and pd.notna(row['LONGITUDE']):
            # Get color and icon based on location type (strip whitespace from category)
            category = str(row['CATEGORY']).strip()
            color = get_marker_color(category)
            icon = get_marker_icon(category)
            
            # Create popup HTML
            popup_html = create_popup_html(
                row['NAME'],
                row['DESCRIPTION'],
                row['IMAGE_URL']
            )
            
            # Add marker to map
            folium.Marker(
                location=[row['LATITUDE'], row['LONGITUDE']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row['NAME'],
                icon=folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(m)
            
            print(f"  ✓ Added: {row['NAME']} ({row['CATEGORY']})")
    
    # Save the map
    print(f"\n💾 Saving map to: {output_file}")
    m.save(output_file)
    print(f"✅ Map created successfully! Open {output_file} in your browser to view.")
    
    # Save geocoded coordinates back to CSV for future use
    df.to_csv(csv_file, index=False)
    print(f"💾 Updated {csv_file} with geocoded coordinates")

# Run the script
if __name__ == "__main__":
    # Create the map using your Hometown Map Data.csv
    create_hometown_map('Hometown Map Data.csv', 'hometown_map.html')
