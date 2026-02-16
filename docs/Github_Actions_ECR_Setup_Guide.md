# GitHub Actions ECR Setup Guide

Complete guide to set up automated Docker builds and ECR pushes via GitHub Actions.

---

## Prerequisites

Before setting up GitHub Actions, you need:

1. AWS account with ECR access
2. GitHub repository
3. AWS IAM role for GitHub Actions
4. ECR repository created

---

## Step 1: Create ECR Repository

### Via AWS CLI:

```bash
aws ecr create-repository \
  --repository-name tab-saver-api \
  --region us-east-1
```

Save the repository URI from the output (e.g., `366579856667.dkr.ecr.us-east-1.amazonaws.com/tab-saver-api`)

### Via AWS Console:

1. Go to AWS Console → ECR → Repositories
2. Click "Create repository"
3. Repository name: `tab-saver-api`
4. Keep default settings
5. Click "Create repository"
6. Copy the repository URI

---

## Step 2: Create IAM Role for GitHub Actions

GitHub Actions needs an AWS role to push images to ECR. We'll use OIDC (no long-lived credentials needed).

### Step 2a: Create Trust Policy

Create a file called `trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringLike": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:YOUR_USERNAME/tab-saver-api:*"
        }
      }
    }
  ]
}
```

**Replace:**
- `ACCOUNT_ID` → Your AWS Account ID (find in AWS Console → Account)
- `YOUR_USERNAME` → Your GitHub username

**Find your AWS Account ID:**
```bash
aws sts get-caller-identity --query Account --output text
```

### Step 2b: Create IAM Role

```bash
aws iam create-role \
  --role-name github-actions-ecr-role \
  --assume-role-policy-document file://trust-policy.json
```

### Step 2c: Create and Attach Permissions Policy

Create a file called `ecr-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GetAuthorizationToken",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowPushToECR",
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeImages"
      ],
      "Resource": "arn:aws:ecr:us-east-1:ACCOUNT_ID:repository/tab-saver-api"
    }
  ]
}
```

**Replace:**
- `ACCOUNT_ID` → Your AWS Account ID

Attach the policy:

```bash
aws iam put-role-policy \
  --role-name github-actions-ecr-role \
  --policy-name ecr-access \
  --policy-document file://ecr-policy.json
```

### Step 2d: Get the Role ARN

```bash
aws iam get-role --role-name github-actions-ecr-role --query 'Role.Arn' --output text
```

Save this ARN (should look like: `arn:aws:iam::366579856667:role/github-actions-ecr-role`)

---

## Step 3: Add GitHub Secret

1. Go to your GitHub repository
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `AWS_ROLE_ARN`
5. Value: The role ARN from Step 2d
6. Click "Add secret"

---

## Step 4: Add GitHub Actions Workflow

### Create workflow file

Create `.github/workflows/build-and-push.yml`:

```yaml
name: Build and Push to ECR

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  REPOSITORY: tab-saver-api
  IMAGE_TAG: ${{ github.sha }}

permissions:
  contents: read
  id-token: write

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      - name: Install dependencies
        run: uv sync --all-extras
      
      - name: Format check with black
        run: uv run black --check src/ tests/
      
      - name: Lint with ruff
        run: uv run ruff check src/ tests/
      
      - name: Run unit tests with coverage
        run: uv run pytest tests/ -v --cov=src --cov-report=xml --cov-fail-under=80
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          fail_ci_if_error: false

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build Docker image
        env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          docker build -t $REGISTRY/$REPOSITORY:$IMAGE_TAG .
          docker build -t $REGISTRY/$REPOSITORY:latest .
      
      - name: Push image to Amazon ECR
        env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          docker push $REGISTRY/$REPOSITORY:$IMAGE_TAG
          docker push $REGISTRY/$REPOSITORY:latest
      
      - name: Print image URI
        env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          echo "✅ Image pushed successfully!"
          echo "Image URI: $REGISTRY/$REPOSITORY:$IMAGE_TAG"
          echo "Latest URI: $REGISTRY/$REPOSITORY:latest"

  notify:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: always()
    
    steps:
      - name: Build status
        run: |
          if [ "${{ needs.build-and-push.result }}" == "success" ]; then
            echo "✅ Docker image built and pushed successfully!"
            echo "Repository: ${{ env.REPOSITORY }}"
            echo "Image Tag: ${{ env.IMAGE_TAG }}"
          else
            echo "❌ Docker build or push failed!"
            exit 1
          fi
```

### Commit and push

```bash
git add .github/workflows/build-and-push.yml
git commit -m "ci: add ECR build and push workflow"
git push origin main
```

---

## Step 5: Monitor Workflow

1. Go to your GitHub repo → Actions
2. Click the latest workflow run
3. Watch the steps execute:
   - ✅ Test job (black, ruff, pytest)
   - ✅ Build Docker image
   - ✅ Push to ECR
   - ✅ Notify

---

## Verify Images in ECR

### Via AWS CLI:

```bash
# List all images
aws ecr describe-images \
  --repository-name tab-saver-api \
  --region us-east-1

# Show image tags and timestamps
aws ecr describe-images \
  --repository-name tab-saver-api \
  --region us-east-1 \
  --query 'imageDetails[*].[imageTags,imagePushedAt]' \
  --output table
```

### Via AWS Console:

1. Go to ECR → Repositories
2. Click `tab-saver-api`
3. See all image tags and push dates

---

## Testing the Image Locally

### Login to ECR

Before pulling images from ECR, you need to authenticate Docker with your AWS account.

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 366579856667.dkr.ecr.us-east-1.amazonaws.com
```

**Replace `366579856667` with your AWS Account ID**

You should see:
```
Login Succeeded
```

### Get your AWS Account ID

If you don't know your account ID:
```bash
aws sts get-caller-identity --query Account --output text
```

Then use it in the login command:
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
```

This command:
1. Gets your AWS Account ID automatically
2. Gets an ECR authentication token
3. Logs Docker in to ECR

### Pull the image

```bash
docker pull 366579856667.dkr.ecr.us-east-1.amazonaws.com/tab-saver-api:latest
```

### Run locally

```bash
docker run -p 5000:5000 366579856667.dkr.ecr.us-east-1.amazonaws.com/tab-saver-api:latest
```

### Test the API

```bash
# In another terminal
curl http://localhost:5000/api/health

# Should return:
# {"status":"ok","timestamp":"2026-02-16T...","tabs_stored":0}
```

---

## Troubleshooting

### "pull access denied"

You need to login to ECR first:
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 366579856667.dkr.ecr.us-east-1.amazonaws.com
```

### "No such file or directory (os error 2)"

In GitHub Actions, this means the workflow couldn't find the Docker command. Make sure:
- Docker is installed (it is, on ubuntu-latest)
- Dockerfile exists in repo root
- All dependencies are in pyproject.toml

### "AccessDenied: User is not authorized"

Check your IAM policy:
```bash
aws iam get-role-policy \
  --role-name github-actions-ecr-role \
  --policy-name ecr-access
```

Verify the policy has all required actions.

### GitHub Actions fails with "credential error"

Check the role ARN in your GitHub secret:
```bash
# In GitHub repo → Settings → Secrets
# Verify AWS_ROLE_ARN is correct
```

Should be: `arn:aws:iam::366579856667:role/github-actions-ecr-role`

### Tests fail, build is skipped

This is expected! The build only runs if tests pass. Fix the failing tests:

```bash
# Run locally
uv run pytest tests/ -v --cov=src

# Fix issues
uv run black src/ tests/
uv run ruff check --fix src/ tests/

# Push again
git add .
git commit -m "fix: resolve test failures"
git push origin main
```

---

## Complete Setup Checklist

- [ ] ECR repository created (`tab-saver-api`)
- [ ] IAM role created (`github-actions-ecr-role`)
- [ ] Trust policy configured for GitHub
- [ ] ECR permissions policy attached
- [ ] Role ARN copied
- [ ] GitHub secret `AWS_ROLE_ARN` added
- [ ] Workflow file `.github/workflows/build-and-push.yml` created
- [ ] Code pushed to main
- [ ] GitHub Actions workflow ran successfully
- [ ] Images appear in ECR
- [ ] Can pull and run image locally

---

## Next Steps

Once images are in ECR and tested locally, you can:

1. **Deploy to AWS Lambda** using Terraform
2. **Update Lambda function** to use the ECR image
3. **Update iOS app** to use Lambda API endpoint

See the infrastructure setup guide for Lambda deployment.

---

## Security Best Practices

✅ **We're doing right:**
- Using OIDC (no long-lived credentials)
- Limiting to specific GitHub repository
- Least privilege IAM policy (only ECR access)
- Image tagged with commit SHA (immutable)
- Tests run before building (quality gate)

✅ **Additional hardening:**
- Images are read-only in ECR
- Use `latest` tag cautiously (points to newest)
- Scan images for vulnerabilities:
  ```bash
  aws ecr start-image-scan \
    --repository-name tab-saver-api \
    --image-id imageTag=latest
  ```

---

## Summary

You now have:
- ✅ ECR repository for Docker images
- ✅ GitHub Actions that tests code
- ✅ GitHub Actions that builds Docker images
- ✅ GitHub Actions that pushes to ECR
- ✅ Secure OIDC authentication (no long-lived keys)

This is **production-grade CI/CD**! 🚀