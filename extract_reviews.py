import json
import csv
from datetime import datetime

with open('answer.json', 'r', encoding='utf-8') as f:
    data = f.read()
    json_start = data.find('{"3447977320"')
    json_end = data.find('</script>')
    json_data = data[json_start:json_end]
    data = json.loads(json_data)

reviews = []
product_name = ""
if '3447977320' in data:
    product_data = data['3447977320']['b']
    reviews = product_data['reviews']
    product_name = product_data['name']

reviews.sort(key=lambda x: x['createdAt'], reverse=True)

with open('reviews.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, lineterminator='\n')
    writer.writerow(['Platform', 'Product Name', 'Date', 'Rating', 'Review Text'])
    
    for review in reviews:
        try:
            date = datetime.strptime(review['createdAt'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            try:
                date = datetime.strptime(review['createdAt'].split('Z')[0], '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                date = datetime.strptime(review['createdAt'].split('T')[0], '%Y-%m-%d')
        
        date_str = date.strftime('%Y-%m-%d')
        review_text = review['text'].replace('\n', ' ').replace('\r', ' ').strip()
        writer.writerow([
            'Лента',
            product_name,
            date_str,
            review['rating'],
            review_text
        ])

print("Reviews have been saved to reviews.csv")