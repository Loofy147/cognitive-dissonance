# Runbook: Automatic rollback on Golden accuracy drop
Trigger: Golden accuracy drop > 1.5% sustained for 30 minutes
Actions:
1. Auto-rollback: fetch last stable snapshot from MLflow and redeploy
2. Notify on-call: post to Slack/email
3. Open incident ticket and attach logs
4. Run lightweight diagnostics: CLG, D trend, KL values
5. If stable: create hotfix branch and disable Critic-generator until root cause found