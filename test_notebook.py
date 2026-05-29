import json
with open('cesar-sentiment/notebooks/cesar_sentiment_simple.ipynb') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if 'def walk_forward' in ''.join(cell.get('source', [])):
        source = ''.join(cell['source'])
        print(source)
