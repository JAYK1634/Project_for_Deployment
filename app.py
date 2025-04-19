from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure Gemini API
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDRQWMO2wHO3YW_LgCtAoukdWW6PLZCJvc")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# MongoDB Connection (Optional)
try:
    from pymongo.mongo_client import MongoClient
    from pymongo.server_api import ServerApi

    # Use the new SQL connection string from MongoDB Atlas
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://atlas-sql-6802a96b0afbe35fcbdfffef-j3xhv.a.query.mongodb.net/hindi_summarizer?ssl=true&authSource=admin")

    client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    client.admin.command('ping')  # Check connection
    db = client["hindi_summarizer"]
    summaries_collection = db["summaries"]
    mongodb_available = True
    print("✅ Pinged MongoDB. Successfully connected!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    mongodb_available = False


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/db-status')
def db_status():
    if mongodb_available:
        try:
            # Test the connection is still working
            client.server_info()
            return "Database connected and working properly"
        except:
            return "Database connection error"
    else:
        return "Database not configured"

@app.route('/summarize', methods=["POST"])
def summarize():
    input_text = request.form["text"]
    
    if input_text.strip() == "":
        return render_template("index.html", summary="⚠️ कृपया सारांश करने के लिए हिंदी टेक्स्ट दर्ज करें।")
    
    # Get user preferences for length
    length = request.form.get("length", "short")
    
    try:
        # Create appropriate instruction based on length
        if length == "short":
            prompt = f"""निम्नलिखित हिंदी टेक्स्ट का एक संक्षिप्त सारांश पैराग्राफ के रूप में बनाएं। कृपया 3-4 वाक्यों में मुख्य विचारों को कवर करें:

{input_text}"""
        else:  # long
            prompt = f"""निम्नलिखित हिंदी टेक्स्ट का एक विस्तृत सारांश पैराग्राफ के रूप में बनाएं। कृपया 8-10 वाक्यों में सभी महत्वपूर्ण विचारों और जानकारी को कवर करें:

{input_text}"""
        
        # Generate summary using Gemini
        response = model.generate_content(prompt)
        summary = response.text
        
        # Calculate compression ratio
        input_words = len(input_text.split())
        summary_words = len(summary.split())
        if input_words > 0:
            compression = f"{(1 - summary_words/input_words) * 100:.1f}%"
            compression_value = (1 - summary_words/input_words) * 100
        else:
            compression = "N/A"
            compression_value = 0
        
        # Count sentences and words in the input text
        sentences = len([s for s in input_text.split('।') if s.strip()])
        words = len(input_text.split())
        
        # Save to MongoDB if available
        if mongodb_available:
            try:
                summary_data = {
                    "original_text": input_text,
                    "summary_text": summary,
                    "length": length,
                    "original_sentences": sentences,
                    "original_words": words,
                    "summary_words": summary_words,
                    "compression_percentage": compression_value,
                    "created_at": datetime.now()
                }
                
                # Insert the summary into MongoDB
                summaries_collection.insert_one(summary_data)
            except Exception as e:
                print(f"MongoDB save error: {e}")
                # Continue with the application even if MongoDB save fails
        
    except Exception as e:
        summary = f"❌ त्रुटि: {str(e)}"
        compression = "N/A"
        sentences = 0
        words = 0
    
    return render_template("index.html", 
                          summary=summary, 
                          input_text=input_text,
                          length=length,
                          sentences=sentences,
                          words=words,
                          compression=compression)

if __name__ == "__main__":
    app.run(debug=True)
