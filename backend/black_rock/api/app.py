@app.route('/api/protocols', methods=['GET'])
def get_protocols():
    try:
        protocols = {
            "POS Terminal -101.1 (4-digit approval)": {
                "approval_length": 4
            },
            "POS Terminal -101.4 (6-digit approval)": {
                "approval_length": 6
            },
            "POS Terminal -101.6 (Pre-authorization)": {
                "approval_length": 6
            },
            "POS Terminal -101.7 (4-digit approval)": {
                "approval_length": 4
            },
            "POS Terminal -101.8 (PIN-LESS transaction)": {
                "approval_length": 4
            },
            "POS Terminal -201.1 (6-digit approval)": {
                "approval_length": 6
            },
            "POS Terminal -201.3 (6-digit approval)": {
                "approval_length": 6
            },
            "POS Terminal -201.5 (6-digit approval)": {
                "approval_length": 6
            }
        }
        return jsonify({
            "success": True,
            "protocols": protocols
        }), 200

    except Exception as e:
        logger.error(f"Failed to load protocols: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Failed to load protocols: {str(e)}"
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
