import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
import mysql.connector
import argparse

def save_output_to_file(output, filename):
    with open(filename, 'w') as file:
        file.write(output)

# Connect to MySQL server
try:
    conn = mysql.connector.connect(
        host='65.19.141.77',
        port='3306',
        user='spinnerx_superuser',
        password='S*e3h2p44',
        database='spinnerx_footballscoores'
    )
    cursor = conn.cursor()
except mysql.connector.Error as e:
    error_message = f"Error connecting to the database: {e}"
    print(error_message)
    save_output_to_file(error_message, "error.txt")
    exit()

# Load teams from the database
try:
    cursor.execute("SELECT DISTINCT home_team, away_team FROM football_scores")
    teams = [team for team_tuple in cursor.fetchall() for team in team_tuple]
    teams = sorted(set(teams))
except mysql.connector.Error as e:
    error_message = f"Error loading teams from the database: {e}"
    print(error_message)
    save_output_to_file(error_message, "error.txt")
    conn.close()
    exit()

# Load match data from the database
try:
    cursor.execute("SELECT home_team, away_team, home_score, away_score FROM football_scores")
    match_data = cursor.fetchall()
except mysql.connector.Error as e:
    error_message = f"Error loading match data from the database: {e}"
    print(error_message)
    save_output_to_file(error_message, "error.txt")
    conn.close()
    exit()

# Preprocess the data
input_data = []
for match in match_data:
    home_team, away_team, home_score, away_score = match
    if home_score is None or away_score is None:
        continue  # Skip matches with missing scores

    if home_score > away_score:
        outcome = 2  # Win
    elif home_score < away_score:
        outcome = 0  # Lose
    else:
        outcome = 1  # Draw

    input_data.append([home_team, away_team, outcome])

input_data = pd.DataFrame(input_data, columns=['home', 'away', 'outcome'])
specific_team_data = pd.get_dummies(input_data, columns=['home', 'away'])

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    specific_team_data.drop('outcome', axis=1),
    specific_team_data['outcome'],
    test_size=0.2,
    random_state=42
)

# Prepare the features (X) and target (y)
X = X_train
y = y_train

# Get team pairs from the input file
team_pairs = []
with open('input_teams.txt', 'r') as file:
    for line in file:
        home_team, away_team = line.strip().split(' - ')
        team_pairs.append((home_team, away_team))

# Perform predictions for each team pair
for specific_team, opposing_team in team_pairs:
    filtered_data = input_data[
        ((input_data['home'] == specific_team) & (input_data['away'] == opposing_team)) |
        ((input_data['home'] == opposing_team) & (input_data['away'] == specific_team))
    ]

    if filtered_data.empty:
        error_message = f"No historical matches found between {specific_team} and {opposing_team}."
        print(error_message)
        save_output_to_file(error_message, f"output_{specific_team}_{opposing_team}.txt")
        continue

    filtered_data = pd.get_dummies(filtered_data, columns=['home', 'away'])
    X_filtered = filtered_data.drop('outcome', axis=1)
    y_filtered = filtered_data['outcome']
    num_matches = len(filtered_data)

    if num_matches < 7:
        error_message = f"Not enough historical matches between {specific_team} and {opposing_team} to make a reliable prediction."
        print(error_message)
        save_output_to_file(error_message, f"output_{specific_team}_{opposing_team}.txt")
        continue

    team1_vs_team2 = filtered_data[
        (filtered_data[f'home_{specific_team}'] == 1) & (filtered_data[f'away_{opposing_team}'] == 1)
    ]
    team2_vs_team1 = filtered_data[
        (filtered_data[f'home_{opposing_team}'] == 1) & (filtered_data[f'away_{specific_team}'] == 1)
    ]

    team1_vs_team2_stats = team1_vs_team2['outcome'].value_counts().to_dict()
    team2_vs_team1_stats = team2_vs_team1['outcome'].value_counts().to_dict()

    match_statistics = f"Total matches between {specific_team} and {opposing_team}: {num_matches}\n\n{specific_team} vs {opposing_team}:\nWins: {team1_vs_team2_stats.get(2, 0)}\nDraws: {team1_vs_team2_stats.get(1, 0)}\nLosses: {team1_vs_team2_stats.get(0, 0)}\n\n{opposing_team} vs {specific_team}:\nWins: {team2_vs_team1_stats.get(2, 0)}\nDraws: {team2_vs_team1_stats.get(1, 0)}\nLosses: {team2_vs_team1_stats.get(0, 0)}"

    all_output_message = f"{match_statistics}\n\n"

    # Perform predictions using different models
    models = ['lr', 'rf', 'svm', 'xgb']
    for model in models:
        if model == 'lr':
            model_instance = LogisticRegression()
        elif model == 'rf':
            model_instance = RandomForestClassifier()
        elif model == 'svm':
            model_instance = SVC(probability=True)
        elif model == 'xgb':
            model_instance = XGBClassifier()

        try:
            model_instance.fit(X_filtered, y_filtered)
        except ValueError as e:
            error_message = f"Error training the {model} model: {e}"
            print(error_message)
            save_output_to_file(error_message, f"error_{specific_team}_{opposing_team}.txt")
            continue

        future_match_data = pd.DataFrame({
            'home_' + specific_team: [0],
            'away_' + specific_team: [1],
            'home_' + opposing_team: [1],
            'away_' + opposing_team: [0]
        })

        missing_features = [f for f in X_filtered.columns if f not in future_match_data.columns]
        future_match_data = pd.concat([future_match_data, pd.DataFrame(columns=missing_features)], axis=1)
        future_match_data = future_match_data.fillna(0)
        future_match_data = future_match_data[X_filtered.columns]

        try:
            prediction = model_instance.predict(future_match_data)
            probabilities = model_instance.predict_proba(future_match_data)[0]
        except ValueError as e:
            error_message = f"Error making predictions with {model} model: {e}"
            print(error_message)
            save_output_to_file(error_message, f"error_{specific_team}_{opposing_team}.txt")
            continue

        outcome_mapping = {2: 'Win', 1: 'Draw', 0: 'Lose'}
        win_threshold = 0.4
        draw_threshold = 0.3

        if probabilities[0] >= win_threshold:
            predicted_outcome_label = 'Win'
        elif probabilities[1] >= draw_threshold:
            predicted_outcome_label = 'Draw'
        else:
            predicted_outcome_label = 'Lose'

        output_message = f"\n\n{model.upper()} Model Results:\nPredicted Outcome: {predicted_outcome_label}\nWin Probability (%): {probabilities[0]*100:.2f}\nDraw Probability (%): {probabilities[1]*100:.2f}\nLose Probability (%): {probabilities[2]*100:.2f}"

        all_output_message += output_message
        print(output_message)

    save_output_to_file(all_output_message, f"all_output_{specific_team}_{opposing_team}.txt")

# Close the database connection
conn.close()