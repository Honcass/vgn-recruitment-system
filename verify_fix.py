import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app import app
from flask import render_template
import sqlite3

def verify_template():
    print("Testing dashboard.html rendering...")
    with app.app_context():
        # Mock applicant data matching the schema used in dashboard.html
        # a[0]: id, a[1]: surname, a[2]: firstname, a[3]: phone, a[4]: address, 
        # a[5]: nok, a[6]: nin, a[7]: photo, a[8]: guarantor, a[9]: status, a[10]: age, a[11]: previous_work
        mock_applicants = [
            ('test_id', 'Doe', "O'Connor", '08012345678', '123 Lagos', 
             'Jane Doe', '12345678901', 'photo.jpg', None, 'Pending', 25, 'Previous Job')
        ]
        
        try:
            with app.test_request_context():
                # This should trigger the filter if it's used in the template
                rendered = render_template('dashboard.html', applicants=mock_applicants)
                print("SUCCESS: Dashboard rendered correctly.")
                
                # Check if 'O\'Connor' is in the rendered output (escaped by addslashes)
                if "O\\'Connor" in rendered:
                    print("SUCCESS: 'O\'Connor' was correctly escaped to 'O\\'Connor'.")
                else:
                    print("WARNING: Escaped name not found in rendered output. Check if addslashes is applied to firstname/surname.")
                    
        except Exception as e:
            print(f"FAILED: Template rendering error: {e}")

if __name__ == "__main__":
    verify_template()
