import requests
import os

def test_upload():
    url = "http://127.0.0.1:8000/api/upload"
    login_url = "http://127.0.0.1:8000/login"

    # Create session
    s = requests.Session()
    
    # Login
    r = s.post(login_url, data={"username": "admin", "password": "changeme"})
    if r.status_code != 200: # It redirects to 303 then 200
         print(f"Login status: {r.status_code}")

    # Create dummy image
    from PIL import Image
    img = Image.new('RGB', (100, 100), color = 'red')
    img.save('test_img.jpg')

    # Upload
    with open('test_img.jpg', 'rb') as f:
        files = {'file': f}
        data = {'path': ''}
        r = s.post(url, files=files, data=data)
        
    print(f"Upload Status: {r.status_code}")
    print(f"Response: {r.text}")

    # Clean up
    if os.path.exists('test_img.jpg'):
        os.remove('test_img.jpg')

if __name__ == "__main__":
    try:
        test_upload()
    except Exception as e:
        print(e)
