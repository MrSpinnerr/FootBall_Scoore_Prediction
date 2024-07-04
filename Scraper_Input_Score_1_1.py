import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Set the start and end dates
start_date = datetime(2024, 5, 18)  # Today's date
end_date = start_date  # We'll only scrape data for today

# Function to scrape match results for a given date
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

            matches.append((home_team, away_team, home_score, away_score))

    return matches

# Main function to scrape and write match results to a text file
def main():
    all_matches = []
    for i in range((end_date - start_date).days + 1):
        date = start_date + timedelta(days=i)
        matches = scrape_match_results(date)
        all_matches.extend(matches)

    # Write the match results to a text file
    with open("match_results.txt", "w") as output_file:   
        for home_team, away_team, home_score, away_score in all_matches:
            output_file.write(f"{home_team} - {away_team}\n")

    print("Match results have been written to match_results.txt")

if __name__ == "__main__":
    main()