
import pandas as pd
from app_store_scraper import AppStore
import json
import time
from datetime import datetime, timedelta

def scrape_app_details_and_reviews(app_name_or_id, country_code, reviews_number=200 ):
    """
    Scrapes app details and a specific number of reviews for an app/
    Can accept either app_name or app_id.
    """
    try:
        if isinstance(app_name_or_id, int):
            app = AppStore(country=country_code, app_id=app_name_or_id)
            print(f"--- Scraping data for App ID: '{app_name_or_id}' in country code: '{country_code}' ---")
        else:
            app = AppStore(country=country_code, app_id=app_name_or_id)
            print(f"--- Scraping data for App Name: '{app_name_or_id}' in country code: '{country_code}' ---")

        app.get_app_details()
        actual_app_name = app.app_info.get('trackName', app_name_or_id)
        print(f"App details fetched for '{actual_app_name}'.")

        app.review(how_many = reviews_number)
        print(f"Attempting to scrape {reviews_number} reviews for '{actual_app_name}'.")

        if not app.reviews:
            print(f"No reviews found for '{actual_app_name}' or an error occurred during review scraping.")
            reviews_df = pd.DataFrane()
        else:
            reviews_df = pd.DataFrame(app.reviews)
            print(f"Successfully scraped {len(reviews_df)} reviews for '{actual_app_name}'.")

        app_info = {
            'app_name': actual_app_name,
            'country_code': country_code,
            'app_id': app_name_or_id,
            'developer_name' : app.app_info.get('sellerName'),
            'primary_genre' : app.app_info.get('primaryGenre'),
            'average_user_rating' : app.app_info.get('averageUserRating'),
            'user_rating_count' : app.app_info.get('userRatingCount'),
            'current_version_release_date' : app.app_info.get('currentVersionReleaseDate'),
            'original_release_date' : app.app_info.get('releaseDate'),
            'price' : app.app_info.get('price'),
            'currency' : app.app_info.get('currency'),
        }

        if not reviews_df.empty:
            reviews_df['app_name'] = actual_app_name
            reviews_df['country_code'] = country_code
            reviews_df['app_id'] = app_name_or_id

        return {'app_info': app_info, 'reviews': reviews_df}

    except Exception as e:
        print(f"An error occurred while scraping data for '{app_name_or_id}': {e}")
        return None

def main():
    SEARCH_TERMS = ["productivity app", "education app", "note taking app", "study tool", "learning game"]
    COUNTRY_CODE = "us"
    MAX_SEARCH_RESULTS_PER_TERM = 20
    NUM_REVIEWS_PER_APP = 100
    MAX_APPS_TO_SCRAPE_AFTER_SEARCH = 30

    unique_app_ids = set()
    apps_from_search = []

    print ("--- Starting app search by keywords ---")
    for term in SEARCH_TERMS:
        print(f"Searching for '{term}' in {COUNTRY_CODE}...")
        try:
            search_results = AppStore(country= COUNTRY_CODE, app_name = term).search(limit = MAX_SEARCH_RESULTS_PER_TERM)
            for app_data in search_results:
                app_id = app_data.get('trackId')
                app_name = app_data.get('appName')
                if app_id and app_id not in unique_app_ids:
                    apps_from_search.append({"name" : app_name, "id" : app_id, "country" : COUNTRY_CODE})
                    unique_app_ids.add(app_id)
            print(f"Found {len(search_results)} apps for '{term}'. Total unique apps found so far: {len(unique_app_ids)}")
            time.sleep(2)
        except Exception as e:
            print(f"Error during app search for {term} : {e}")

    print(f"\n--- Total unique apps found from search: {len(apps_from_search)} ---")
    if not apps_from_search:
        print("No apps found from search. Please try different search terms or country codes")
        return
    apps_to_detail_scrape = apps_from_search[:MAX_APPS_TO_SCRAPE_AFTER_SEARCH]
    print(f"Proceeding to detail scrape {len(apps_to_detail_scrape)} apps.")

    ALL_REVIEWS_DF = pd.DataFrame()
    ALL_APP_INFO_LIST = []

    for app_config in apps_to_detail_scrape:
        app_id_to_scrape = app_config["id"]
        country_code = app_config["country"]

        scraped_data = scrape_app_details_and_reviews(app_id_to_scrape,country_code, NUM_REVIEWS_PER_APP)

        if scraped_data:
            ALL_APP_INFO_LIST.append(scraped_data['app_info'])
            ALL_REVIEWS_DF = pd.concat([ALL_REVIEWS_DF, scraped_data['reviews_df']], ignore_index=True)
            time.sleep(7)

    if not ALL_APP_INFO_LIST:
        print("No ap information was successfully scraped.")
        return

    app_info_df = pd.DataFrame(ALL_APP_INFO_LIST)

    print("\n--- Initial Data Cleaning and Analysis ---")

    app_info_df['original_release_date'] = pd.to_datetime(app_info_df['original_release_date'], errors='coerce')
    app_info_df['current_version_release_date'] = pd.to_datetime(app_info_df['current_version_release_date'], errors='coerce')
    app_info_df['app_age_dats'] = (datetime.now() - app_info_df['original_release_date']).dt.days

    recent_apps_df = app_info_df[app_info_df['app_age_days'] <= (365 * 2)].copy()
    print(f"Apps released in the last 2 years: {len(recent_apps_df)}")

    trending_new_apps = recent_apps_df.sort_values(by='user_rating_count', ascending=False)

    print("\n--- Top 10 'Newer' Apps (by user rating count) in Productivity/Education ---")
    print(trending_new_apps[['app_name', 'primary_genre', 'original_release_date', 'app_age_days', 'user_rating_count',
                             'average_user_rating']].head(10))

    print("\n--- Basic Analysis of Combined Reviews ---")
    if not ALL_REVIEWS_DF.empty:
        print(f"Total reviews across all scrapred apps: {len(ALL_REVIEWS_DF)}")
        print("\nTop 5 rows of combined reviews:")
        print(ALL_REVIEWS_DF.head())
        print("\nValue counts for 'taring' across all apps:")
        print(ALL_REVIEWS_DF['taring'].value_counts().sort_index(ascending=False))
        print("\nMissing values in reviews:")
        print(ALL_REVIEWS_DF.isnull().sum())
    else:
        print("No reviews were collected.")

    try:
        app_info_output = "app_info_productivity_education_from_scratch.csv"
        ALL_REVIEWS_DF.to_csv("app_reviews_productivity_education_from_search.csv")
        app_info_df.to_csv(app_info_output, index=False, encoding='utf-8')
        print(f"\nAPP review data saved to 'app_reviews_productivity_education_from_search.csv'")
        print(f"App genreal info saved to'{app_info_output}'")
    except Exception as e:
        print(f"Error saving combined data to CSV: {e}")

if __name__ == "__main__":
    main()



