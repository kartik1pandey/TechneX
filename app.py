import googleapiclient.discovery
import googleapiclient.errors
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import CountVectorizer
from flask import Flask, request, render_template, jsonify
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# YouTube API setup
api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = "AIzaSyCODIhWd7oRQT4mm-MIdqB_s5Fwzqc9kiQ"  # Replace with your actual YouTube Data API key

youtube = googleapiclient.discovery.build(
    api_service_name, api_version, developerKey=DEVELOPER_KEY
)

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
            # Pagination
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

# Route for the homepage
@app.route('/')
def home():
    return render_template('index.html')

# Route to handle video URL submission
@app.route('/analyze', methods=['POST'])
def analyze():
    video_url = request.form['video_url']
    parsed_url = urlparse(video_url)
    video_id = parse_qs(parsed_url.query).get('v', [None])[0]
    
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    # Get comments DataFrame
    df = get_comments(video_id)
    if isinstance(df, dict) and "error" in df:
        return jsonify(df), 500
    
    # Add sentiment analysis
    df = analyze_sentiment(df)
    
    # Calculate sentiment summary
    sentiment_summary = {
        "positive": len(df[df['sentiment_label'] == 'positive']),
        "negative": len(df[df['sentiment_label'] == 'negative']),
        "neutral": len(df[df['sentiment_label'] == 'neutral']),
        "total": len(df)
    }
    
    # Get key phrases and suggestions
    key_phrases = get_key_phrases(df, 'negative')
    suggestions = ["Consider addressing feedback about: " + ", ".join(key_phrases)] if key_phrases else ["No major negative themes detected."]
    
    # Convert DataFrame to JSON-friendly format
    result = df.to_dict(orient='records')
    return jsonify({
        "comments": result,
        "summary": sentiment_summary,
        "key_phrases": key_phrases,
        "suggestions": suggestions
    })

if __name__ == "__main__":
    app.run(debug=True)
