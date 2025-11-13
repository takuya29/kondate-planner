# Kondate Planner - Cost Estimation Guide

**Last Updated**: November 2025
**Region**: ap-northeast-1 (Tokyo)

This document provides detailed cost estimates for running the Kondate Planner application on AWS.

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [AWS Services Used](#aws-services-used)
3. [Pricing Details by Service](#pricing-details-by-service)
4. [Usage Scenarios & Cost Estimates](#usage-scenarios--cost-estimates)
5. [Cost Optimization Strategies](#cost-optimization-strategies)
6. [Monthly Cost Breakdown](#monthly-cost-breakdown)

---

## Executive Summary

**Estimated Monthly Cost Range**: $5-$50 USD/month

The Kondate Planner is a serverless application with costs that scale based on usage. The primary cost driver is **Amazon Bedrock** (AI model inference), followed by Lambda execution costs.

**Cost Breakdown by Service** (typical usage):
- **Amazon Bedrock**: 70-85% of total cost
- **AWS Lambda**: 10-20% of total cost
- **DynamoDB**: 5-10% of total cost
- **CloudWatch Logs**: <5% of total cost
- **AWS Chatbot**: $0 (free tier)

---

## AWS Services Used

Based on `template.yaml` analysis:

| Service | Resource | Configuration |
|---------|----------|---------------|
| **Amazon Bedrock** | Agent + Foundation Model | Claude Sonnet 4.5 (default) via inference profile |
| **AWS Lambda** | 3 Functions | Python 3.12, 256MB, ARM64, 30s timeout |
| **DynamoDB** | 2 Tables | On-demand billing, 1 GSI |
| **AWS Chatbot** | Slack integration | Amazon Q Developer |
| **CloudWatch** | Logs | Lambda and Agent logs |

---

## Pricing Details by Service

### 1. Amazon Bedrock (Claude Models)

**Claude Sonnet 4.5** (Japan geo-cross-region inference):
- **Input tokens**: $3.30 per million tokens (~10% premium for Japan geo)
- **Output tokens**: $16.50 per million tokens
- **Best for**: Highest quality responses, complex reasoning

**Claude Haiku 4.5** (cost-effective alternative):
- **Input tokens**: ~$0.40 per million tokens (estimated)
- **Output tokens**: ~$2.00 per million tokens (estimated)
- **Best for**: Cost optimization, simpler interactions

**Token Estimation**:
- Average input per interaction: 2,000-3,000 tokens (includes agent instructions + action results)
- Average output per interaction: 500-800 tokens (menu suggestions)

**Cost per interaction** (Sonnet 4.5):
- Input: (2,500 tokens / 1,000,000) × $3.30 = $0.00825
- Output: (650 tokens / 1,000,000) × $16.50 = $0.01073
- **Total per interaction**: ~$0.019 ($0.02)

**Cost per interaction** (Haiku 4.5):
- Input: (2,500 tokens / 1,000,000) × $0.40 = $0.001
- Output: (650 tokens / 1,000,000) × $2.00 = $0.0013
- **Total per interaction**: ~$0.0023 (less than 1 cent)

### 2. AWS Lambda (Tokyo, ARM64)

**Pricing** (ap-northeast-1):
- **Requests**: $0.20 per million requests
- **Compute (256MB ARM64)**: ~$0.0000033 per 100ms (ARM64 discount applied)

**Typical execution**:
- Average duration per function: 500-1000ms
- 3 functions invoked per agent interaction
- **Cost per interaction**: ~$0.0001 (negligible)

**Monthly cost** (500 interactions/month):
- Requests: (500 × 3) / 1,000,000 × $0.20 = $0.0003
- Compute: 500 × 3 × 0.75s × $0.0000033 = $0.0037
- **Total Lambda**: ~$0.004/month (less than 1 cent)

### 3. DynamoDB (On-Demand)

**Pricing** (ap-northeast-1, after Nov 2024 price reduction):
- **Write Request Units**: ~$1.44 per million WRUs (50% reduction applied)
- **Read Request Units**: ~$0.29 per million RRUs (50% reduction applied)
- **Storage**: $0.285 per GB/month

**Typical usage**:
- Recipe database: ~100 recipes × 2KB = 200KB (~0.0002 GB)
- Menu history: ~365 days × 1KB = 365KB (~0.0004 GB)
- **Total storage**: ~0.001 GB = **$0.0003/month**

**Request costs** (500 interactions/month):
- Reads (get_recipes, get_history): ~1,500 RRUs = $0.0004
- Writes (save_menu): ~500 WRUs = $0.0007
- **Total DynamoDB**: ~$0.002/month (negligible)

### 4. AWS Chatbot / Amazon Q Developer

**Pricing**: **$0/month** (Free tier)
- Generative AI features in chat applications are free
- No additional cost for Slack integration

### 5. CloudWatch Logs

**Pricing**:
- **Ingestion**: $0.76 per GB (Tokyo)
- **Storage**: $0.033 per GB/month

**Typical usage**:
- Lambda logs: ~10MB/month
- Bedrock Agent logs: ~5MB/month
- **Total**: ~15MB = **$0.01/month**

---

## Usage Scenarios & Cost Estimates

### Scenario 1: Light Usage (Individual/Testing)
**Profile**:
- 50 interactions/month
- 1-2 times per week
- Mostly menu suggestions and history checks

**Monthly Cost Breakdown**:
| Service | Cost |
|---------|------|
| Bedrock (Sonnet 4.5) | $1.00 |
| Lambda | $0.01 |
| DynamoDB | $0.01 |
| CloudWatch | $0.01 |
| **Total** | **~$1.03/month** |

**With Haiku 4.5**: **~$0.15/month**

---

### Scenario 2: Regular Usage (Small Team/Family)
**Profile**:
- 200 interactions/month
- Daily usage
- Menu planning + recipe exploration

**Monthly Cost Breakdown**:
| Service | Cost |
|---------|------|
| Bedrock (Sonnet 4.5) | $4.00 |
| Lambda | $0.02 |
| DynamoDB | $0.02 |
| CloudWatch | $0.01 |
| **Total** | **~$4.05/month** |

**With Haiku 4.5**: **~$0.50/month**

---

### Scenario 3: Heavy Usage (Organization/Production)
**Profile**:
- 1,000 interactions/month
- Multiple users
- Extensive menu planning and history tracking

**Monthly Cost Breakdown**:
| Service | Cost |
|---------|------|
| Bedrock (Sonnet 4.5) | $20.00 |
| Lambda | $0.10 |
| DynamoDB | $0.10 |
| CloudWatch | $0.05 |
| **Total** | **~$20.25/month** |

**With Haiku 4.5**: **~$2.50/month**

---

### Scenario 4: Enterprise Usage
**Profile**:
- 5,000 interactions/month
- Large team/community
- High-frequency usage

**Monthly Cost Breakdown**:
| Service | Cost |
|---------|------|
| Bedrock (Sonnet 4.5) | $100.00 |
| Lambda | $0.50 |
| DynamoDB | $0.50 |
| CloudWatch | $0.25 |
| **Total** | **~$101.25/month** |

**With Haiku 4.5**: **~$12.50/month**

---

## Cost Optimization Strategies

### 1. Switch to Claude Haiku 4.5 (Recommended)
**Savings**: **88-90% reduction** in Bedrock costs

Deploy with Haiku:
```bash
sam deploy --parameter-overrides \
  BedrockInferenceProfile="jp.anthropic.claude-haiku-4-5-20251001-v1:0"
```

**Trade-offs**:
- Slightly less sophisticated responses
- Still excellent for menu planning tasks
- Recommended for cost-conscious deployments

### 2. Implement Prompt Caching
**Savings**: Up to 90% on repeated context

Amazon Bedrock supports prompt caching for Claude models. This caches the agent instructions and frequently accessed data, reducing input token costs.

**Implementation**: Add caching headers to Bedrock Agent API calls (requires custom implementation)

### 3. Use Batch Processing
**Savings**: 50% cost reduction

For non-real-time operations (e.g., weekly meal planning), use Bedrock batch processing instead of synchronous inference.

### 4. Set Lambda Memory Appropriately
**Current**: 256MB (conservative)
**Optimization**: Test with 128MB to reduce costs by 50%

```bash
# Update template.yaml Globals section
MemorySize: 128
```

**Risk**: May increase execution time if memory-constrained

### 5. DynamoDB Reserved Capacity (Advanced)
**When**: If you hit >100k requests/month consistently
**Savings**: Up to 50% vs on-demand

Not recommended for typical usage patterns.

### 6. CloudWatch Logs Retention
Set shorter retention periods:

```yaml
# Add to Lambda function definitions
LoggingConfig:
  LogGroup: !Ref MyLogGroup

MyLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    RetentionInDays: 7  # Default is "Never expire"
```

**Savings**: Reduces storage costs for logs

### 7. Implement Rate Limiting
Add rate limiting in Slack to prevent accidental high usage:
- Max 10 interactions per user per hour
- Daily caps per team

---

## Monthly Cost Breakdown

### Cost Comparison: Sonnet vs Haiku

| Usage Level | Interactions/Month | Sonnet 4.5 | Haiku 4.5 | Savings |
|-------------|-------------------|------------|-----------|---------|
| Light | 50 | $1.03 | $0.15 | 85% |
| Regular | 200 | $4.05 | $0.50 | 88% |
| Heavy | 1,000 | $20.25 | $2.50 | 88% |
| Enterprise | 5,000 | $101.25 | $12.50 | 88% |

### Cost Distribution (Sonnet 4.5, Regular Usage)

```
Amazon Bedrock:  98.8%  ████████████████████████████████████████
Lambda:           0.5%  ▏
DynamoDB:         0.5%  ▏
CloudWatch:       0.2%  ▏
```

### Cost Distribution (Haiku 4.5, Regular Usage)

```
Amazon Bedrock:  90.0%  █████████████████████████████████████
Lambda:           4.0%  ███
DynamoDB:         4.0%  ███
CloudWatch:       2.0%  ██
```

---

## Additional Considerations

### Free Tier Benefits (First 12 Months)

If your AWS account is within the first 12 months:
- **Lambda**: 1M free requests + 400,000 GB-seconds compute
- **DynamoDB**: 25 GB storage + 25 WRUs + 25 RRUs
- **CloudWatch**: 5 GB ingestion + 5 GB storage

**Impact**: First year costs could be near-zero for light usage (Bedrock is not included in free tier)

### Data Transfer Costs

**Within AWS**: No cost for data transfer between Lambda, DynamoDB, and Bedrock in the same region (Tokyo)

**To Slack**: Minimal (<1MB per interaction), covered by free tier (1 GB/month free outbound)

### Hidden Costs to Watch

1. **Bedrock Agent Versioning**: Creating new agent versions doesn't incur storage costs
2. **IAM/CloudFormation**: No direct costs
3. **S3 for SAM deployments**: ~$0.01/month (negligible)

---

## Recommendations

### For Individual Users / Testing
✅ **Use Claude Haiku 4.5** - Excellent quality at <$1/month
✅ Keep on-demand DynamoDB billing
✅ Monitor usage via CloudWatch dashboards (free)

### For Small Teams (2-5 users)
✅ **Start with Haiku 4.5**, upgrade to Sonnet if quality issues
✅ Set CloudWatch log retention to 7 days
✅ Implement basic rate limiting in Slack

### For Production/Enterprise
✅ **Evaluate Sonnet vs Haiku** based on quality requirements
✅ Implement prompt caching for recurring context
✅ Set up AWS Cost Anomaly Detection
✅ Consider batch processing for bulk operations
✅ Use AWS Budgets to set spending alerts

---

## Monitoring & Cost Tracking

### Set Up AWS Budgets

```bash
# Create a $10 monthly budget with alerts
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

### CloudWatch Cost Metrics

Monitor these metrics:
- `AWS/Bedrock` → `ModelInvocationCount`, `TokenCount`
- `AWS/Lambda` → `Invocations`, `Duration`
- `AWS/DynamoDB` → `ConsumedReadCapacityUnits`, `ConsumedWriteCapacityUnits`

### Cost Allocation Tags

Add tags to resources for better cost tracking:

```yaml
# In template.yaml, add to each resource
Tags:
  - Key: Project
    Value: kondate-planner
  - Key: Environment
    Value: production
  - Key: CostCenter
    Value: engineering
```

---

## Conclusion

The Kondate Planner application is highly cost-efficient, with estimated monthly costs ranging from **$0.15 to $20** for typical usage scenarios.

**Key Takeaways**:
1. **Bedrock (AI) is the primary cost** (85-98% of total)
2. **Switching to Haiku 4.5 saves ~88%** with minimal quality impact
3. **Lambda, DynamoDB, and other services are negligible** (<$0.10/month)
4. **AWS Chatbot/Slack integration is free**
5. **Serverless architecture means you only pay for what you use**

For most users, **running this application will cost less than a cup of coffee per month** ☕

---

## Questions or Issues?

If you have questions about costs or need help optimizing:
1. Check AWS Cost Explorer for actual usage
2. Review CloudWatch metrics for usage patterns
3. File an issue on GitHub: https://github.com/your-repo/kondate-planner/issues

---

**Document Version**: 1.0
**Author**: Claude (AI Assistant)
**License**: MIT
