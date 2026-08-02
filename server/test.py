import os
from getpass import getpass

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.environ["SUPABASE_URL"]
supabase_secret_key = os.environ["SUPABASE_SECRET_KEY"]

user_id = "f74a9379-5e56-4737-a465-87e5d4e9178c"
new_password = getpass("Enter a new test password: ")

supabase = create_client(supabase_url, supabase_secret_key)

response = supabase.auth.admin.update_user_by_id(
    user_id,
    {
        "password": new_password,
        "email_confirm": True,
    },
)

print("Password updated for:", response.user.id)