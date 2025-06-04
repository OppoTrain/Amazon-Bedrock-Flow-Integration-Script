#!/usr/bin/env python3
"""
Amazon Bedrock Flow Integration Script
This script demonstrates how to integrate Amazon Bedrock Flows into your application.
"""

import json
import boto3
import requests
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass
from flask import Flask, request, jsonify, render_template_string
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BedrockFlowConfig:
    """Configuration for Bedrock Flow"""
    flow_id: str
    flow_alias_id: str
    region: str = 'us-east-1'
    api_gateway_url: Optional[str] = None

class BedrockFlowClient:
    """Client for interacting with Amazon Bedrock Flows"""
    
    def __init__(self, config: BedrockFlowConfig):
        self.config = config
        self.bedrock_agent = boto3.client(
            'bedrock-agent-runtime',
            region_name=config.region
        )
    
    def invoke_flow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a Bedrock Flow with input data
        
        Args:
            input_data: Dictionary containing the input for the flow
            
        Returns:
            Dictionary containing the flow response
        """
        try:
            logger.info(f"Invoking Bedrock Flow {self.config.flow_id}")
            
            # Prepare the request
            request_body = {
                'flowIdentifier': self.config.flow_id,
                'flowAliasIdentifier': self.config.flow_alias_id,
                'inputs': [
                    {
                        'content': input_data,
                        'nodeName': 'FlowInputNode',  # Adjust based on your flow
                        'nodeOutputName': 'document'   # Adjust based on your flow
                    }
                ]
            }
            
            # Invoke the flow
            response = self.bedrock_agent.invoke_flow(**request_body)
            
            # Process the response
            result = self._process_flow_response(response)
            
            logger.info("Flow invocation successful")
            return result
            
        except Exception as e:
            logger.error(f"Error invoking Bedrock Flow: {str(e)}")
            raise
    
    def _process_flow_response(self, response) -> Dict[str, Any]:
        """Process the raw Bedrock Flow response"""
        try:
            # Extract the response body
            response_body = response.get('responseStream')
            
            if response_body:
                # Process streaming response
                result = []
                for event in response_body:
                    if 'flowOutputEvent' in event:
                        output = event['flowOutputEvent']
                        result.append(output)
                
                return {
                    'success': True,
                    'data': result,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'No response from flow',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing flow response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

class BedrockFlowAPI:
    """API wrapper for Bedrock Flow integration"""
    
    def __init__(self, flow_client: BedrockFlowClient):
        self.flow_client = flow_client
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes for the API"""
        
        @self.app.route('/')
        def index():
            """Serve a simple HTML interface"""
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Bedrock Flow Integration</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .input-section { margin-bottom: 20px; }
                    textarea { width: 100%; height: 100px; margin: 10px 0; }
                    button { background-color: #007cba; color: white; padding: 10px 20px; border: none; cursor: pointer; }
                    .response { margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }
                    .error { background-color: #ffebee; color: #c62828; }
                    .success { background-color: #e8f5e8; color: #2e7d32; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Amazon Bedrock Flow Integration</h1>
                    <div class="input-section">
                        <h3>Send Input to Bedrock Flow</h3>
                        <textarea id="userInput" placeholder="Enter your input here..."></textarea>
                        <br>
                        <button onclick="sendToFlow()">Send to Flow</button>
                    </div>
                    <div id="response" class="response" style="display:none;"></div>
                </div>
                
                <script>
                    async function sendToFlow() {
                        const input = document.getElementById('userInput').value;
                        const responseDiv = document.getElementById('response');
                        
                        if (!input.trim()) {
                            alert('Please enter some input');
                            return;
                        }
                        
                        try {
                            responseDiv.style.display = 'block';
                            responseDiv.innerHTML = 'Processing...';
                            responseDiv.className = 'response';
                            
                            const response = await fetch('/invoke-flow', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({ input: input })
                            });
                            
                            const result = await response.json();
                            
                            if (result.success) {
                                responseDiv.className = 'response success';
                                responseDiv.innerHTML = '<h4>Flow Response:</h4><pre>' + JSON.stringify(result.data, null, 2) + '</pre>';
                            } else {
                                responseDiv.className = 'response error';
                                responseDiv.innerHTML = '<h4>Error:</h4><p>' + result.error + '</p>';
                            }
                        } catch (error) {
                            responseDiv.className = 'response error';
                            responseDiv.innerHTML = '<h4>Error:</h4><p>' + error.message + '</p>';
                        }
                    }
                </script>
            </body>
            </html>
            """
            return html_template
        
        @self.app.route('/invoke-flow', methods=['POST'])
        def invoke_flow():
            """API endpoint to invoke the Bedrock Flow"""
            try:
                data = request.get_json()
                user_input = data.get('input', '')
                
                if not user_input:
                    return jsonify({
                        'success': False,
                        'error': 'No input provided'
                    }), 400
                
                # Prepare input for the flow
                flow_input = {
                    'query': user_input,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Invoke the flow
                result = self.flow_client.invoke_flow(flow_input)
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Error in invoke_flow endpoint: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat()
            })
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the Flask application"""
        self.app.run(host=host, port=port, debug=debug)

class BedrockFlowIntegration:
    """Main class for Bedrock Flow integration"""
    
    def __init__(self, flow_id: str, flow_alias_id: str, region: str = 'us-east-1'):
        self.config = BedrockFlowConfig(
            flow_id=flow_id,
            flow_alias_id=flow_alias_id,
            region=region
        )
        self.client = BedrockFlowClient(self.config)
        self.api = BedrockFlowAPI(self.client)
    
    def test_flow(self, test_input: str) -> Dict[str, Any]:
        """Test the flow with a simple input"""
        try:
            logger.info(f"Testing flow with input: {test_input}")
            
            flow_input = {
                'query': test_input,
                'timestamp': datetime.now().isoformat()
            }
            
            result = self.client.invoke_flow(flow_input)
            return result
            
        except Exception as e:
            logger.error(f"Error testing flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_server(self, host='0.0.0.0', port=5000, debug=False):
        """Run the web server"""
        logger.info(f"Starting Bedrock Flow API server on {host}:{port}")
        self.api.run(host=host, port=port, debug=debug)

# Example usage and configuration
def main():
    """Main function to demonstrate usage"""
    
    # Configuration - Replace with your actual values
    FLOW_ID = "YOUR_FLOW_ID"  # Replace with your Bedrock Flow ID
    FLOW_ALIAS_ID = "YOUR_FLOW_ALIAS_ID"  # Replace with your Flow Alias ID
    REGION = "us-east-1"  # Replace with your preferred region
    
    # Environment variable fallbacks
    FLOW_ID = os.getenv('BEDROCK_FLOW_ID', FLOW_ID)
    FLOW_ALIAS_ID = os.getenv('BEDROCK_FLOW_ALIAS_ID', FLOW_ALIAS_ID)
    REGION = os.getenv('AWS_REGION', REGION)
    
    try:
        # Initialize the integration
        integration = BedrockFlowIntegration(
            flow_id=FLOW_ID,
            flow_alias_id=FLOW_ALIAS_ID,
            region=REGION
        )
        
        # Test the flow (optional)
        print("Testing Bedrock Flow...")
        test_result = integration.test_flow("Hello, this is a test message")
        print(f"Test result: {json.dumps(test_result, indent=2)}")
        
        # Start the web server
        print("Starting web server...")
        print("Access the web interface at: http://localhost:5000")
        integration.run_server(debug=True)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
        print("\nMake sure to:")
        print("1. Replace YOUR_FLOW_ID with your actual Bedrock Flow ID")
        print("2. Replace YOUR_FLOW_ALIAS_ID with your actual Flow Alias ID")
        print("3. Configure your AWS credentials")
        print("4. Install required dependencies: pip install boto3 flask requests")

if __name__ == "__main__":
    main()
