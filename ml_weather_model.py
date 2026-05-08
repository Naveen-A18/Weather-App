import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression

CSV_FILE = "data/weather_data.csv"

# Load data
data = pd.read_csv(CSV_FILE)

# Basic check
print("Total records:", len(data))
print(data.head())

# Simple features: humidity, wind
X = data[["humidity", "wind"]]
y = data["temp"]

# Train-test split
X_train, X_test, Y_train, Y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = LinearRegression()
model.fit(X_train, Y_train)

score = model.score(X_test, Y_test)
print(f"\nModel R² score: {score:.3f}")

# Test with one example
if len(X_test) > 0:
    sample = X_test.iloc[0:1]
    true_temp = Y_test.iloc[0]
    pred_temp = model.predict(sample)[0]

    print("\nExample Prediction:")
    print("Humidity:", sample['humidity'].values[0])
    print("Wind   :", sample['wind'].values[0])
    print(f"True Temp      : {true_temp:.2f}°C")
    print(f"Predicted Temp : {pred_temp:.2f}°C")
