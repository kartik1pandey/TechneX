import googleapiclient.discovery
import googleapiclient.errors
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import CountVectorizer
from flask import Flask, request, render_template, jsonify, send_file
from urllib.parse import urlparse, parse_qs
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
import io
import google.generativeai as genai
import re

app = Flask(__name__)

# YouTube API setup
api_service_name = "youtube"
api_version = "v3"
YOUTUBE_API_KEY = "AIzaSyCODIhWd7oRQT4mm-MIdqB_s5Fwzqc9kiQ"  # Replace with your actual YouTube Data API key
youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=YOUTUBE_API_KEY)

# Gemini API setup
GEMINI_API_KEY = "AIzaSyASxUMihUbMeqchDANe5PIYEWDMwbkbXec"  # Replace with your actual Gemini API key
genai.configure(api_key=GEMINI_API_KEY)

# Initialize VADER sentiment analyzer
nltk.download('vader_lexicon')
sid = SentimentIntensityAnalyzer()

def get_comments(video_id):
    comments = []
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100
        )
        while request:
            response = request.execute()
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append([
                    comment['authorDisplayName'],
                    comment['publishedAt'],
                    comment['updatedAt'],
                    comment['likeCount'],
                    comment['textDisplay']
                ])
            if 'nextPageToken' in response:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=100,
                    pageToken=response['nextPageToken']
                )
            else:
                break
    except googleapiclient.errors.HttpError as e:
        return {"error": str(e)}
    
    df = pd.DataFrame(comments, columns=['author', 'published_at', 'updated_at', 'like_count', 'text'])
    return df

def analyze_sentiment(df):
    df['sentiment'] = df['text'].apply(lambda text: sid.polarity_scores(text)['compound'])
    df['sentiment_label'] = df['sentiment'].apply(
        lambda score: 'positive' if score >= 0.05 else ('negative' if score <= -0.05 else 'neutral')
    )
    return df

def get_key_phrases(df, sentiment='negative', top_n=5):
    filtered_comments = df[df['sentiment_label'] == sentiment]['text']
    if len(filtered_comments) == 0:
        return []
    vectorizer = CountVectorizer(stop_words='english', ngram_range=(1, 2))
    X = vectorizer.fit_transform(filtered_comments)
    word_counts = pd.DataFrame(X.toarray(), columns=vectorizer.get_feature_names_out())
    top_phrases = word_counts.sum().sort_values(ascending=False).head(top_n).index.tolist()
    return top_phrases

def analyze_with_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")  # Use "gemini-2.0-flash" if available
    response = model.generate_content(prompt)
    return response.text

def generate_summary_and_sentiment(comments):
    prompt = f"""Here are some YouTube comments:
    {comments}

    1. Provide a brief summary of the video's main topics in plain text.
    2. Identify the most repeated opinions or phrases.
    3. Determine the overall sentiment (positive, negative, neutral).
    4. Keep it short, about 50 words.
    5. Format it with bullets using <b> tags for headings (e.g., <b>Summary:</b>, <b>Repeated Opinions:</b>, <b>Sentiment:</b>) instead of asterisks."""
    
    return analyze_with_gemini(prompt)

def generate_chatbot_response(video_summary, user_input):
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""The following is a summary of a YouTube video formatted with HTML tags:

    {video_summary}

    Answer the following question based on the video context, and format your response with HTML tags:
    - Use <h1> for main headings (e.g., <h1>Response</h1>).
    - Use <b> for subheadings or emphasis (e.g., <b>Key Points:</b>).
    - Use <p> for paragraphs.
    - Avoid asterisks (*) for formatting.

    Question: {user_input}"""
    
    response = model.generate_content(prompt)
    return response.text

def generate_pdf_report(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("YouTube Comment Sentiment Analysis Report", styles['Title']))
    story.append(Spacer(1, 12))

    summary_text = f"Total Comments: {data['summary']['total']}<br/>Positive: {data['summary']['positive']}<br/>Negative: {data['summary']['negative']}<br/>Neutral: {data['summary']['neutral']}"
    story.append(Paragraph("Sentiment Summary", styles['Heading2']))
    story.append(Paragraph(summary_text, styles['Normal']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Top Negative Key Phrases", styles['Heading2']))
    phrases = ", ".join(data['key_phrases']) if data['key_phrases'] else "None detected"
    story.append(Paragraph(phrases, styles['Normal']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Suggestions", styles['Heading2']))
    story.append(Paragraph(data['suggestions'][0], styles['Normal']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Chatbot Summary", styles['Heading2']))
    story.append(Paragraph(data['chatbot_summary'], styles['Normal']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Top Comments", styles['Heading2']))
    top_comments = [[c['author'], c['text'], c['sentiment_label'], c['like_count']] for c in data['comments'][:5]]
    table_data = [['Author', 'Comment', 'Sentiment', 'Likes']] + top_comments
    table = Table(table_data, colWidths=[100, 200, 80, 50])
    table.setStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)])
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    video_url = request.form['video_url']
    parsed_url = urlparse(video_url)
    video_id = parse_qs(parsed_url.query).get('v', [None])[0]
    
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    df = get_comments(video_id)
    if isinstance(df, dict) and "error" in df:
        return jsonify(df), 500
    
    df = analyze_sentiment(df)
    
    sentiment_summary = {
        "positive": len(df[df['sentiment_label'] == 'positive']),
        "negative": len(df[df['sentiment_label'] == 'negative']),
        "neutral": len(df[df['sentiment_label'] == 'neutral']),
        "total": len(df)
    }
    
    key_phrases = get_key_phrases(df, 'negative')
    suggestions = ["Consider addressing feedback about: " + ", ".join(key_phrases)] if key_phrases else ["No major negative themes detected."]
    
    comments_list = df['text'].tolist()
    chatbot_summary = generate_summary_and_sentiment(comments_list)
    
    result = df.to_dict(orient='records')
    return jsonify({
        "comments": result,
        "summary": sentiment_summary,
        "key_phrases": key_phrases,
        "suggestions": suggestions,
        "chatbot_summary": chatbot_summary,
        "video_url": video_url
    })

@app.route('/chatbot', methods=['POST'])
def chatbot_endpoint():
    data = request.get_json()
    video_summary = data.get('chatbot_summary')
    user_input = data.get('user_input')
    
    if not video_summary or not user_input:
        return jsonify({"error": "Missing summary or user input"}), 400
    
    response = generate_chatbot_response(video_summary, user_input)
    return jsonify({"response": response})

@app.route('/download_report', methods=['POST'])
def download_report():
    data = request.get_json()
    pdf_buffer = generate_pdf_report(data)
    return send_file(pdf_buffer, as_attachment=True, download_name="sentiment_report.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)
