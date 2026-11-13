import logging
import db
from app import APP

"""
Server Entry Point
------------------
Configures logging and starts the Flask application on a specific port.
Designed to match project requirements: http://localhost:9001/
"""

# Configure standard logging format to track server events and SQL queries
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOG = logging.getLogger(__name__)

if __name__ == '__main__':
    # Initialize the database connection (Compatibility call)
    db.connect()
    
    LOG.info("Starting application on port 9001...")
    
    # Run the Flask app
    # host='0.0.0.0' makes the server accessible externally
    # port=9001 is the required port for the project
    APP.run(host='0.0.0.0', port=9001, debug=True)