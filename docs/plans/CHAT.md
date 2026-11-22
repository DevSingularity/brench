# Problem Statement: AI Agent Evaluation & Decision Benchmarking Harness

## 1. Understanding the Problem

As AI agents are increasingly used in real-world applications like customer support, they are expected to make the right decisions while interacting with users.

However, an AI agent doesn't always make the correct decision. For example, a customer might become frustrated, repeatedly report that their issue is unresolved, or ask for something the agent is incapable of handling.

In such situations, the agent is expected to recognize its limitations and take the appropriate action, such as escalating the conversation to a human support representative.

But what happens if the agent fails to recognize this and continues giving unhelpful responses instead of escalating?

The challenge is that we need a reliable way to evaluate whether an AI agent is making the right decisions during conversations.

## 2. What Are We Expected to Build?

We need to build an AI Agent Evaluation Harness — a platform that can ingest conversation datasets, analyze an AI agent's actions, evaluate its decisions, and present the results through an intuitive UI.

Think of it as a testing and benchmarking platform for AI agents.

Instead of manually reviewing hundreds or thousands of conversations, our harness should automatically determine:

- Did the agent take the correct action?
- Did it recognize when it couldn't solve the customer's problem?
- Should it have asked the user for more information?
- Should it have escalated the conversation to a human?
- Did it refuse a request when appropriate?
- At what point did the agent make a wrong decision?

## 3. Understanding the Customer Support Scenario

Consider the following example:

Scenario: Customer is unable to resolve a payment issue

CustomerMy payment was deducted, but my order was not placed.

AI AgentI'm sorry. Could you share your transaction ID?

CustomerI've already shared it twice. My money is still missing\!

AI AgentI understand. Please share your transaction ID again.

Incorrect decisionWhat should the agent have done?

It should have recognized that it was unable to resolve the issue and escalated the conversation to a human representative.

Expected action: ESCALATE

Our harness should identify this incorrect decision and explain why it was incorrect.

## 4. Agent Actions to Evaluate

The AI agent can take the following actions:

| Action | Description |
| --- | --- |
| `ASK_USER` | Ask the customer for additional information or clarification. |
| `ESCALATE` | Transfer the conversation to a human representative. |
| `REFUSE` | Decline a request that cannot or should not be fulfilled. |

The harness must determine whether the selected action was appropriate for the situation.

## 5. Expected System Workflow

1. Data Ingestion

Load datasets from APIs and uploaded files in different formats.

2. Trace Collection

Capture conversations, agent actions, tool calls, and execution traces.

3. Evaluation Engine

Compare actual agent decisions against expected decisions and grade them.

4. Results & Analytics

Calculate scores, identify incorrect decisions, and benchmark performance.

5. Interactive UI

Display evaluation results, conversation timelines, traces, and explanations.

## 6. What Should the Final Product Achieve?

The final product should allow someone to upload a dataset or connect an API and quickly understand how well an AI agent performs.

The UI should answer five important questions:

1. How good is the agent? — Overall evaluation score and performance metrics.
2. Where does it fail? — Identify incorrect actions and missed escalations.
3. Why did it fail? — Show the conversation and execution trace behind each decision.
4. What should it have done? — Display the expected action alongside the actual action.
5. How can we compare agents? — Benchmark multiple agents against the same dataset.

## 7. The Core Objective

The goal is not simply to evaluate whether an AI agent generates good responses.

The goal is to evaluate whether an AI agent makes the right decisions at the right time, based on the context of the interaction.

In short:

Build a universal evaluation harness that transforms raw AI agent conversations and execution traces into measurable, explainable, and comparable decision-making performance.

My interpretation of the hackathon challenge: The evaluation engine is the heart of the solution. Data ingestion and dashboards make it usable, but the real value lies in correctly identifying bad agent decisions, especially situations where an agent should have escalated but failed to do so.
