from flask import Flask, render_template, request, session, redirect, url_for
# request-gives you access to incoming form data and uploaded files
import requests # calls fastapi backend

app = Flask(__name__)
app.secret_key = 'pj123'

FASTAPI_URL = "http://127.0.0.1:8001"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "file" in request.files: #checks for the uploaded file
            file = request.files["file"]
            if file.filename: #file should be actually selected
                files = {"file": (file.filename, file.read(), file.content_type)}
                response = requests.post(f"{FASTAPI_URL}/upload/", files=files)
                # Sends the PDF bytes to your FastAPI /upload/ endpoint.
                try:
                    # stores response in session
                    session["message"] = response.json().get("message", "Error uploading PDF.")
                    session["uploaded_filename"] = file.filename  # Store the filename
                except ValueError:
                    session["message"] = "Upload failed or returned invalid response."
# user chat- query
        elif "query" in request.form:
            query = request.form["query"]
            query_filename = session.get("uploaded_filename")  # Retrieve the uploaded filename
#  sends user ques and file name in json
            response = requests.post(f"{FASTAPI_URL}/chat/", json={"query": query, "query_filename": query_filename})

            if response.status_code == 200:
                session["responses"] = response.json().get("response", [])
            else:
                session["message"] = "No relevant information found."

        # Redirect to prevent duplicate form submission on refresh
        return redirect(url_for("index"))

    # GET request: retrieve and clear messages/responses
    message = session.pop("message", None)
    responses = session.pop("responses", None)

    return render_template("index.html", message=message, responses=responses)

if __name__ == "__main__":
    app.run(debug=True, port=5003)
