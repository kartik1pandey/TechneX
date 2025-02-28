import googleapiclient.discovery
import googleapiclient.errors
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import CountVectorizer
from flask import Flask, request, render_template, jsonify
from urllib.parse import urlparse, parse_qs
from crewai import Agent, Task, Crew
import os
from langchain_groq import ChatGroq

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

# Set up Grok API key for CrewAI
os.environ["GROQ_API_KEY"] = "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"

# Initialize Grok LLM
llm = ChatGroq(
    model="groq/llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY")
)

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

# Define CrewAI Agents with Grok LLM
comment_analyzer = Agent(
    role="Comment Analyzer",
    goal="Analyze YouTube comments for sentiment and key themes",
    backstory="Expert in NLP and sentiment analysis, adept at understanding user feedback.",
    llm=llm,
    verbose=True
)

suggestion_generator = Agent(
    role="Suggestion Generator",
    goal="Provide actionable suggestions based on comment analysis",
    backstory="Skilled in content strategy, offering insights to improve YouTube videos.",
    llm=llm,
    verbose=True
)

# Define Tasks
def analyze_comments_task(comments):
    return Task(
        description=f"Analyze these YouTube comments for sentiment and key themes: {comments}",
        agent=comment_analyzer,
        expected_output="A JSON object with sentiment summary and key negative themes"
    )

def suggest_improvements_task(analysis_result):
    return Task(
        description=f"Based on this analysis: {analysis_result}, provide suggestions to improve the video content.",
        agent=suggestion_generator,
        expected_output="A list of actionable suggestions"
    )

# Route for the homepage
@app.route('/')
def home():
    return render_template('index.html')

# Route to handle video URL submission (for web app) or JSON comments (for extension)
@app.route('/analyze', methods=['POST'])
def analyze():
    # Handle both form submission (web) and JSON (extension)
    if request.is_json:
        data = request.json
        comments_input = data.get('comments', [])
        if not comments_input:
            return jsonify({"error": "No comments provided"}), 400
        
        # Convert list of dicts to DataFrame
        df = pd.DataFrame(comments_input, columns=['author', 'likeCount', 'text'])
        df['published_at'] = ''  # Placeholder for compatibility
        df['updated_at'] = ''    # Placeholder for compatibility
        df = df.rename(columns={'likeCount': 'like_count'})
    else:
        video_url = request.form['video_url']
        parsed_url = urlparse(video_url)
        video_id = parse_qs(parsed_url.query).get('v', [None])[0]
        
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400
        
        # Get comments DataFrame from YouTube API
        df = get_comments(video_id)
        if isinstance(df, dict) and "error" in df:
            return jsonify(df), 500

    # Add sentiment analysis with VADER
    df = analyze_sentiment(df)
    
    # Calculate sentiment summary
    sentiment_summary = {
        "positive": len(df[df['sentiment_label'] == 'positive']),
        "negative": len(df[df['sentiment_label'] == 'negative']),
        "neutral": len(df[df['sentiment_label'] == 'neutral']),
        "total": len(df)
    }
    
    # Get key phrases
    key_phrases = get_key_phrases(df, 'negative')
    
    # Prepare comments for CrewAI (list of dicts)
    comments_list = df[['text', 'author', 'like_count']].to_dict(orient='records')
    
    # Define and run CrewAI tasks
    task1 = analyze_comments_task(comments_list)
    task2 = suggest_improvements_task({"summary": sentiment_summary, "key_phrases": key_phrases})
    crew = Crew(agents=[comment_analyzer, suggestion_generator], tasks=[task1, task2], verbose=True)  # Changed to verbose=True
    result = crew.kickoff()
    
    # Combine results
    response = {
        "comments": df[['text', 'author', 'like_count', 'sentiment_label']].to_dict(orient='records'),
        "summary": sentiment_summary,
        "key_phrases": key_phrases,
        "suggestions": getattr(result.tasks_output[-1], "result", None) if result.tasks_output else None
    }
    
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)