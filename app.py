@app.route('/oracle', methods=['POST'])
def oracle():
    data = request.json
    messages = data.get('messages', [])
    system = data.get('system', '')
    try:
        r = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': ANTHROPIC_KEY,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 1000,
                'system': system,
                'messages': messages
            },
            timeout=30
        )
        result = r.json()
        print("Anthropic response:", result)
        if 'error' in result:
            return jsonify({"text": f"API Error: {result['error']}"})
        return jsonify({"text": result.get('content', [{}])[0].get('text', 'Silent.')})
    except Exception as e:
        print("Oracle error:", str(e))
        return jsonify({"text": f"Error: {str(e)}"})
