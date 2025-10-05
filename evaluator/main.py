import os
import requests
import numpy as np
import time

class EvaluationOrchestrator:
    """
    Orchestrates the full evaluation workflow in a persistent loop by calling all other services.
    """
    def __init__(self):
        self.meta_controller_api_url = os.getenv("META_CONTROLLER_API_URL")
        self.proposer_api_url = os.getenv("PROPOSER_API_URL")
        self.critic_api_url = os.getenv("CRITIC_API_URL")
        self.learner_api_url = os.getenv("LEARNER_API_URL")
        self.safety_gate_api_url = os.getenv("SAFETY_GATE_API_URL")

        self.service_urls = [
            self.meta_controller_api_url,
            self.proposer_api_url,
            self.critic_api_url,
            self.learner_api_url,
            self.safety_gate_api_url,
        ]

        if not all(self.service_urls):
            raise EnvironmentError("All service API URLs must be set.")

        print("--- Evaluation Orchestrator Initialized ---")
        for name, url in self.__dict__.items():
            if "api_url" in name:
                print(f"{name.replace('_', ' ').replace('api url', 'API URL').title()}: {url}")
        print("------------------------------------------")

    def _wait_for_services(self):
        """Checks that all dependent services are available before starting the loop."""
        print("\nWaiting for all services to be ready...")
        for url in self.service_urls:
            while True:
                try:
                    # Use a GET request to the root URL as a health check
                    response = requests.get(f"{url}/", timeout=5)
                    if response.status_code == 200:
                        print(f"  - Service at {url} is ready.")
                        break
                except requests.exceptions.RequestException:
                    print(f"  - Service at {url} not yet available, retrying in 3 seconds...")
                    time.sleep(3)
        print("All services are ready. Starting orchestration loop.")

    def run_persistent_loop(self, interval_seconds=10):
        """
        Executes the evaluation workflow in a continuous loop.
        """
        self._wait_for_services()

        cycle_count = 0
        while True:
            cycle_count += 1
            print(f"\n\n===== Starting Evaluation Cycle {cycle_count} =====")

            try:
                # 1. Get policy from Meta-Controller
                print("\n--- [Step 1] Fetching Policy ---")
                policy_response = requests.get(f"{self.meta_controller_api_url}/policy", timeout=10)
                policy_response.raise_for_status()
                policy_data = policy_response.json()
                print(f"[Meta-Controller Response] Current policy: lambda={policy_data['lambda_val']}, D_target={policy_data['d_target']}")

                # 2. Get prediction from Proposer
                print("\n--- [Step 2] Getting Prediction ---")
                sample_input = {"feature1": np.random.uniform(0, 5), "feature2": np.random.uniform(0, 5)}
                proposer_response = requests.post(f"{self.proposer_api_url}/predict", json=sample_input, timeout=10)
                proposer_response.raise_for_status()
                proposer_data = proposer_response.json()
                print(f"[Proposer Response] Model '{proposer_data['model_id']}' predicted: {proposer_data['prediction']}")

                # 3. Get contradiction from Critic
                print("\n--- [Step 3] Generating Contradiction ---")
                critic_input = {"model_id": proposer_data['model_id'], "prediction": proposer_data['prediction']}
                critic_response = requests.post(f"{self.critic_api_url}/generate_contradiction", json=critic_input, timeout=10)
                critic_response.raise_for_status()
                critic_data = critic_response.json()
                print(f"[Critic Response] Critic '{critic_data['critic_id']}' generated: {critic_data['contradiction']}")

                # 4. Compute Dissonance
                proposal_vec = np.array(proposer_data['prediction'])
                contradiction_vec = np.array(critic_data['contradiction'])
                dissonance_score = np.linalg.norm(proposal_vec - contradiction_vec)
                print(f"\n--- [Step 4] Dissonance Score Calculated ---")
                print(f"  - Score (L2 Distance): {dissonance_score:.4f}")

                # 5. Check with Safety Gate
                print("\n--- [Step 5] Performing Safety Check ---")
                safety_check_input = {"model_id": proposer_data['model_id'], "dissonance_score": dissonance_score}
                safety_response = requests.post(f"{self.safety_gate_api_url}/check", json=safety_check_input, timeout=10)
                safety_response.raise_for_status()
                safety_data = safety_response.json()
                print(f"[Safety Gate Response] Decision: {safety_data['decision']}. Reason: {safety_data['reason']}")

                # 6. Trigger Learner if Safety Gate passes
                if safety_data['decision'] == "PASS":
                    print("\n--- [Step 6] Triggering Learner ---")
                    learner_input = {
                        "model_id": proposer_data['model_id'],
                        "dissonance_score": dissonance_score,
                        "message": "Safety checks passed, proceeding with model update."
                    }
                    learner_response = requests.post(f"{self.learner_api_url}/update", json=learner_input, timeout=10)
                    learner_response.raise_for_status()
                    print(f"[Learner Response] {learner_response.json()['status']}")
                else:
                    print("\n--- [Step 6] Skipping Learner ---")
                    print("  - Reason: Safety Gate did not pass.")

            except requests.exceptions.RequestException as e:
                print(f"\n[ERROR] An error occurred during the evaluation cycle: {e}")
                print("Continuing to the next cycle after a delay.")

            print(f"\n===== Cycle {cycle_count} Complete. Waiting for {interval_seconds} seconds... =====")
            time.sleep(interval_seconds)

if __name__ == "__main__":
    orchestrator = EvaluationOrchestrator()
    orchestrator.run_persistent_loop()