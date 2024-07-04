import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import mysql.connector

# Connect to MySQL database
conn = mysql.connector.connect(
    host='65.19.141.77',
    port='3306',
    user='spinnerx_superuser',
    password='S*e3h2p44',
    database='spinnerx_footballscoores'
)

# Create a table to store the match results
cursor = conn.cursor()
create_table_query = """
CREATE TABLE IF NOT EXISTS football_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE,
    home_team VARCHAR(255),
    away_team VARCHAR(255),
    home_score VARCHAR(10),
    away_score VARCHAR(10)
)
"""
cursor.execute(create_table_query)

def scrape_match_results(date):
    url = f"https://www.soccerbase.com/matches/results.sd?date={date.strftime('%Y-%m-%d')}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    matches = []
    for match_row in soup.select("table.soccerGrid tr.match"):
        details = match_row.select("td")
        if details:
            home_team = details[3].select_one("a").text.strip()
            away_team = details[5].select_one("a").text.strip()
            score_details = details[4].select_one("a")
            if score_details:
                home_score = score_details.text.split("-")[0].strip()
                away_score = score_details.text.split("-")[1].strip()
            else:
                home_score = away_score = ""

            matches.append({
                "date": date.strftime("%Y-%m-%d"),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score
            })

    return matches

# Set the start date
start_date = datetime(2024, 5, 10).date()  # Convert to datetime.date

# Get the current date as the end date
end_date = datetime.now().date() - timedelta(days=1)

all_matches = []
delta = end_date - start_date
total_requests = delta.days + 1

fixtures_written = 0
progress_count = 0

# Insert the scraped match results into the database
insert_query = """
INSERT INTO football_scores (date, home_team, away_team, home_score, away_score)
VALUES (%s, %s, %s, %s, %s)
"""

# Dictionary to keep track of fixture count for each URL
fixtures_count = {}

for i in range(total_requests):
    date = start_date + timedelta(days=i)
    matches = scrape_match_results(date)
    all_matches.extend(matches)

    url = f"https://www.soccerbase.com/matches/results.sd?date={date.strftime('%Y-%m-%d')}"
    fixtures_count[url] = fixtures_count.get(url, 0)  # Initialize fixture count for the URL

    cur = conn.cursor()

    # Loop through each fixture
    for fixture in matches:
        # Check if we have scraped 50 fixtures for this URL
        if fixtures_count[url] >= 50:
            # Save the data to the database
            conn.commit()
            print(f"Saved 50 fixtures to the database for URL: {url}")
            fixtures_count[url] = 0  # Reset fixture count
            cur.close()
            cur = conn.cursor()

        date_with_day = fixture['date']
        home_team = fixture['home_team']
        away_team = fixture['away_team']
        home_score = fixture['home_score']
        away_score = fixture['away_score']

        # Check if the data already exists in the database
        cur.execute("SELECT COUNT(*) FROM football_scores WHERE date = %s AND home_team = %s AND away_team = %s", (date_with_day, home_team, away_team))
        existing_count = cur.fetchone()[0]

        if existing_count == 0:
            values = (date_with_day, home_team, away_team, home_score, away_score)
            cur.execute(insert_query, values)

            # Check if the data was successfully written to the database
            cur.execute("SELECT COUNT(*) FROM football_scores WHERE date = %s AND home_team = %s AND away_team = %s", (date_with_day, home_team, away_team))
            new_count = cur.fetchone()[0]

            if new_count > existing_count:
                fixtures_written += 1
                fixtures_count[url] += 1
            else:
                print(f"Failed to write data for {home_team} vs {away_team} on {date_with_day}")

    # Update the progress count
    progress_count += 1
    print(f'Progress: {progress_count}/{total_requests} (Fixtures written: {fixtures_written})')

    cur.close()

conn.commit()
conn.close()