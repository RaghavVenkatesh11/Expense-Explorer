# Web Application Mimicking Google Sheets

# Step 1: Install required libraries
# Run this command in your environment to install Flask
# pip install flask

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Data storage for the spreadsheet (in-memory for simplicity)
spreadsheet_data = {
    "sheet": [["" for _ in range(10)] for _ in range(10)]  # 10x10 blank grid
}

# Helper function to calculate SUM, AVERAGE, etc.
def calculate_function(function, range_data):
    try:
        flat_data = [float(cell) for row in range_data for cell in row if cell != ""]
        if function == "SUM":
            return sum(flat_data)
        elif function == "AVERAGE":
            return sum(flat_data) / len(flat_data) if flat_data else 0
        elif function == "MAX":
            return max(flat_data)
        elif function == "MIN":
            return min(flat_data)
        elif function == "COUNT":
            return len(flat_data)
    except ValueError:
        return "Error: Non-numeric data in range."

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/update_cell", methods=["POST"])
def update_cell():
    data = request.json
    row, col, value = data["row"], data["col"], data["value"]
    spreadsheet_data["sheet"][row][col] = value
    return jsonify(success=True)

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json
    function, start_row, end_row, start_col, end_col = (
        data["function"],
        data["start_row"],
        data["end_row"],
        data["start_col"],
        data["end_col"],
    )
    range_data = [
        spreadsheet_data["sheet"][r][start_col:end_col + 1]
        for r in range(start_row, end_row + 1)
    ]
    result = calculate_function(function, range_data)
    return jsonify(result=result)

if __name__ == "__main__":
    app.run(debug=True)
