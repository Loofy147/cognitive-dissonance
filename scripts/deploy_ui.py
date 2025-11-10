from huggingface_hub import HfApi, create_repo
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Deploy the Gradio UI to Hugging Face Spaces.")
    parser.add_argument("--hf-token", required=True, help="Your Hugging Face API token.")
    parser.add_argument("--evaluator-url", required=True, help="The URL of the evaluator service.")
    args = parser.parse_args()

    api = HfApi()

    try:
        user = api.whoami(token=args.hf_token)
        username = user["name"]

        repo_name = "gradio-ui-for-self-cognitive-dissonance"
        repo_id = f"{username}/{repo_name}"

        print(f"Creating or updating Hugging Face space: {repo_id}")

        create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="gradio",
            token=args.hf_token,
            exist_ok=True,
        )

        print(f"Uploading files to Hugging Face space: {repo_id}")
        api.upload_folder(
            folder_path="services/ui",
            repo_id=repo_id,
            repo_type="space",
            token=args.hf_token,
        )
        print("Upload successful.")

        print(f"Setting environment variable EVALUATOR_URL to {args.evaluator_url}")
        api.add_space_secret(
            repo_id=repo_id,
            key="EVALUATOR_URL",
            value=args.evaluator_url,
            token=args.hf_token,
        )
        print("Environment variable set.")

    except Exception as e:
        print(f"Failed to deploy to Hugging Face: {e}")
        exit(1)

if __name__ == "__main__":
    main()
