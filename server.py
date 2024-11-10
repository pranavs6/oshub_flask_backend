from flask import Flask, request, jsonify
from transformers import DebertaV2Tokenizer
from celadon.model import MultiHeadDebertaForSequenceClassification
import torch
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
from flask import Flask, request, jsonify
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
import psycopg2
from psycopg2 import sql
from datetime import datetime
import json

app = Flask(__name__)

tokenizer = DebertaV2Tokenizer.from_pretrained("/home/pranavsathyaar/main/works/oshub_flask/celadon")
print("Tokenizer loaded")
model = MultiHeadDebertaForSequenceClassification.from_pretrained("/home/pranavsathyaar/main/works/oshub_flask/celadon")
model.eval()

categories = ['Race/Origin', 'Gender/Sex', 'Religion', 'Ability', 'Violence']
content_queue = []

DB_HOST = "db_public_ip"  
DB_NAME = "db_name"      
DB_USER = "db_user"      
DB_PASSWORD = "password"    
DB_PORT = "5432"

def create_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn

PROJECT_ID = "your_project"
LOCATION = "global"
ENGINE_ID = "your_agent"  

def search_sample(
    project_id: str,
    location: str,
    engine_id: str,
    search_query: str,
) -> discoveryengine.SearchResponse:
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    client = discoveryengine.SearchServiceClient(client_options=client_options)

    serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_config"

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=search_query,
        page_size=10,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    return client.search(request)

@app.route('/add_post', methods=['POST'])
def add_post():
    data = request.json
    post_id = data.get("post_id")
    user_id = data.get("user_id")
    content = data.get("content")
    tags = data.get("tags")
    total_likes = data.get("total_likes", 0)
    total_dislikes = data.get("total_dislikes", 0)
    total_comments = data.get("total_comments", 0)
    created_at = datetime.utcnow()  # Automatic timestamp

    if isinstance(content, str):
        content_json = json.dumps({"text": content})
    elif isinstance(content, dict):
        content_json = json.dumps(content)
    else:
        return jsonify({"error": "Invalid content format"}), 400

    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        insert_query = sql.SQL("""
            INSERT INTO posts (post_id, user_id, content, tags, total_likes, total_dislikes, total_comments, created_at)
            VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
        """)
        
        cursor.execute(insert_query, (post_id, user_id, content_json, tags, total_likes, total_dislikes, total_comments, created_at))
        conn.commit()
        
        return jsonify({"message": "Post added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/search', methods=['POST'])
def search_route():
    data = request.get_json() 
    search_query = data.get('query')     
    if not search_query:
        return jsonify({"error": "Missing search query"}), 400
    
    try:
        response = search_sample(PROJECT_ID, LOCATION, ENGINE_ID, search_query)

        #print("Response:", response)
        post_ids = []
        response_str = str(response)
        #print("Response as string:", response_str)
        pattern = r'key: "post_id"\s+value\s+{\s+number_value: (\d+)'

        post_ids = re.findall(pattern, response_str)

        print("Extracted post_ids:", post_ids)

        return jsonify({"post_ids": post_ids}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500



@app.route('/check', methods=['POST'])
def check():
    data = request.json
    content_holder = data.get('text', '')
    mail_address_holder = data.get('mail_address', '')
    print(content_holder, mail_address_holder)
    content_queue.append((mail_address_holder, content_holder))

    if len(content_queue) > 0:
        toxic = queue_handler()
    
    return jsonify({"toxic": toxic})

def classify(mail_address, content):
    inputs = tokenizer(content, return_tensors="pt", padding=True, truncation=True)
    outputs = model(input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'])

    predictions = outputs.argmax(dim=-1).squeeze().tolist()
    result = {category: 'Toxic' if prediction > 0 else 'Not Toxic' for category, prediction in zip(categories, predictions)}
    
    toxic_flag = any(prediction == 'Toxic' for prediction in result.values())
    
    if toxic_flag:
        report(mail_address, content, result)
    else:
        store(mail_address, content)

    return toxic_flag

def store(mail_address, content):
    print("Safe person:", mail_address, "Content:", content)

def report(mail_address, content, result):
    toxic_categories = [category for category, status in result.items() if status == 'Toxic']
    email_body = f"""Dear user,

Your comment was flagged for containing toxic content in the following category/categories: {', '.join(toxic_categories)}.

Comment: "{content}"

Please review your comment.

Best regards,
OSHUB Team"""

    gmail_user = "mailer_unit" 
    gmail_password = "mailer_password"  

    message = MIMEMultipart()
    message["From"] = gmail_user
    message["To"] = mail_address
    message["Subject"] = "Toxic Content Warning"
    message.attach(MIMEText(email_body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, mail_address, message.as_string())
        server.quit()
        print(f"Email sent to: {mail_address}")
    except Exception as e:
        print(f"Error sending email: {e}")

def queue_handler():
    if content_queue:
        cur = content_queue.pop(0)
        return classify(cur[0], cur[1])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

