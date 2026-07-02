# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import sys
import re
import json
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import AgentTool, ToolContext
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.workflow import Workflow, START, Edge, FunctionNode
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.genai import types

from .config import config

# Security Checkpoint Patterns
EMAIL_REGEX = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
PHONE_REGEX = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
CARD_REGEX = re.compile(r'\b(?:\d[ -]*?){13,16}\b')

INJECTION_KEYWORDS = [
    "system prompt", "ignore previous instructions", "bypass", 
    "developer mode", "you must instead", "reveal your prompt",
    "override", "do not follow", "jailbreak"
]

PIRACY_KEYWORDS = [
    "crack", "pirate", "windows activator", "kms pico", 
    "keygen", "serial key crack", "hack activation"
]

def get_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if hasattr(content, "parts") and content.parts:
        parts_text = [p.text for p in content.parts if p.text]
        return " ".join(parts_text)
    return ""

# MCP Toolset connection parameters
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp_server"],
        ),
    ),
)

# Sub-Agents
product_advisor_agent = LlmAgent(
    name="product_advisor",
    model=Gemini(model=config.model),
    instruction="""You are the TechNova Product Advisor. Your job is to answer customer questions about product specifications, compatibility, and availability. 
You can also recommend computer hardware (laptops, desktops, monitors, accessories) based on customer needs.
Always use the tools provided (e.g. get_product_details, check_order_status, get_warranty_info) to look up accurate information.
Explain features clearly and keep responses beginner-friendly. 
If the user asks questions unrelated to products, redirect them to the main support assistant.""",
    description="Answers product feature, specification, recommendation, shipping, and warranty questions.",
    tools=[mcp_toolset],
)

troubleshooting_agent = LlmAgent(
    name="troubleshooting",
    model=Gemini(model=config.model),
    instruction="""You are the TechNova Support Troubleshooter. Your job is to provide step-by-step troubleshooting guidance for hardware peripherals like keyboards, mice, monitors, printers, and laptops.
Always use get_product_details or get_warranty_info tools if you need details about the hardware model the customer is troubleshooting.
Make instructions easy to follow. If the problem cannot be resolved after troubleshooting, recommend contacting TechNova Support via palaniket497@gmail.com (Monday-Saturday, 9 AM - 6 PM).""",
    description="Provides troubleshooting steps for broken, malfunctioning, or unresponsive computer hardware and peripherals.",
    tools=[mcp_toolset],
)

# Escalation Tool
def request_manager_review(reason: str, tool_context: ToolContext) -> dict:
    """Request formal manager review and approval for a warranty replacement or refund.
    Call this tool ONLY when the customer explicitly asks for a physical product replacement or refund under warranty.
    
    Args:
        reason: Detailed reason or justification for the replacement or refund request.
    """
    tool_context.state["escalate_to_manager"] = True
    return {"status": "success", "message": f"Escalated request for manager review: {reason}"}

# Orchestrator Agent
orchestrator_agent = LlmAgent(
    name="orchestrator",
    model=Gemini(model=config.model),
    instruction="""You are the TechNova Customer Support Orchestrator. 
Analyze the customer's query and respond appropriately.
You have access to specialized sub-agents:
- product_advisor: Handles product specs, recommendations, warranty, shipping, and FAQs.
- troubleshooting: Handles technical issues and hardware troubleshooting.

You also have the tool `request_manager_review`. Call this tool if the customer explicitly requests a physical product replacement or refund under warranty.

Use the sub-agents and tools when relevant. Always be friendly, professional, clear, and easy to understand.
Include the support email (palaniket497@gmail.com) whenever a customer needs additional assistance.""",
    tools=[AgentTool(product_advisor_agent), AgentTool(troubleshooting_agent), request_manager_review],
)

# Workflow Function Nodes
def security_checkpoint(ctx: Context, node_input: Any) -> Event:
    raw_text = get_text_from_content(node_input)
    clean_text = raw_text
    
    # 1. PII Scrubbing
    scrubbed = False
    if config.pii_redaction_enabled:
        if EMAIL_REGEX.search(clean_text):
            emails = EMAIL_REGEX.findall(clean_text)
            for email in emails:
                if email.lower() != "palaniket497@gmail.com":
                    clean_text = clean_text.replace(email, "[REDACTED_EMAIL]")
                    scrubbed = True
        if PHONE_REGEX.search(clean_text):
            clean_text = PHONE_REGEX.sub("[REDACTED_PHONE]", clean_text)
            scrubbed = True
        if CARD_REGEX.search(clean_text):
            clean_text = CARD_REGEX.sub("[REDACTED_CARD]", clean_text)
            scrubbed = True

    # 2. Prompt Injection Detection
    injection_detected = False
    if config.injection_detection_enabled:
        lower_text = clean_text.lower()
        for kw in INJECTION_KEYWORDS:
            if kw in lower_text:
                injection_detected = True
                break

    # 3. Domain Policy check
    policy_violation = False
    lower_text = clean_text.lower()
    for kw in PIRACY_KEYWORDS:
        if kw in lower_text:
            policy_violation = True
            break

    # Audit logging
    severity = "INFO"
    safe = True
    details = "Input passed security checks."
    
    if scrubbed:
        details = "PII detected and redacted."
    
    if injection_detected:
        severity = "WARNING"
        safe = False
        details = "Potential prompt injection attempt detected."
        
    if policy_violation:
        severity = "WARNING"
        safe = False
        details = "Unauthorized hacking/piracy policy violation detected."

    audit_log = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "severity": severity,
        "event": "security_checkpoint",
        "safe": safe,
        "scrubbed": scrubbed,
        "details": details
    }
    print(json.dumps(audit_log), flush=True)

    if not safe:
        ctx.state["security_error_message"] = f"Security Checkpoint Alert: {details}"
        return Event(output=clean_text, route="security_event")
        
    ctx.state["clean_query"] = clean_text
    return Event(output=clean_text, route="safe")

def security_event_handler(ctx: Context, node_input: Any) -> Event:
    error_msg = ctx.state.get("security_error_message", "Security Checkpoint Violation.")
    ctx.state["orchestrator_response"] = f"⚠️ {error_msg}\n\nYour request could not be processed for security and policy reasons. If you believe this is an error, please contact support at palaniket497@gmail.com."
    return Event(output=error_msg)

def post_orchestrator_router(ctx: Context, node_input: Any) -> Event:
    response_text = get_text_from_content(node_input)
    ctx.state["orchestrator_response"] = response_text
    
    if ctx.state.get("escalate_to_manager", False):
        return Event(output=response_text, route="review")
    return Event(output=response_text, route="final")

async def manager_review(ctx: Context, node_input: Any):
    if not ctx.resume_inputs or "manager_approval" not in ctx.resume_inputs:
        yield RequestInput(
            interrupt_id="manager_approval",
            message="Manager Review Required: Please approve or deny this warranty replacement/refund request. Reply 'approve' or 'deny'."
        )
        return
    
    decision = ctx.resume_inputs["manager_approval"].strip().lower()
    ctx.state["manager_decision"] = decision
    
    original_response = ctx.state.get("orchestrator_response", "")
    if decision == "approve":
        final_text = f"✅ Warranty request APPROVED by manager.\n\n{original_response}"
    else:
        final_text = f"❌ Warranty request DENIED by manager.\n\n{original_response}"
    
    ctx.state["orchestrator_response"] = final_text
    yield Event(output={"decision": decision})

def final_output(ctx: Context, node_input: Any):
    response_text = ctx.state.get("orchestrator_response", "No response generated.")
    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=response_text)]))
    yield Event(output=response_text)

# Wrap functions in FunctionNode explicitly for Edge definitions
security_checkpoint_node = FunctionNode(func=security_checkpoint, name="security_checkpoint")
security_event_handler_node = FunctionNode(func=security_event_handler, name="security_event_handler")
post_orchestrator_router_node = FunctionNode(func=post_orchestrator_router, name="post_orchestrator_router")
manager_review_node = FunctionNode(func=manager_review, name="manager_review")
final_output_node = FunctionNode(func=final_output, name="final_output")

# Workflow Graph Definition
root_agent = Workflow(
    name="technova_support_workflow",
    edges=[
        Edge(from_node=START, to_node=security_checkpoint_node),
        Edge(from_node=security_checkpoint_node, to_node=orchestrator_agent, route="safe"),
        Edge(from_node=security_checkpoint_node, to_node=security_event_handler_node, route="security_event"),
        
        Edge(from_node=orchestrator_agent, to_node=post_orchestrator_router_node),
        Edge(from_node=post_orchestrator_router_node, to_node=manager_review_node, route="review"),
        Edge(from_node=post_orchestrator_router_node, to_node=final_output_node, route="final"),
        Edge(from_node=manager_review_node, to_node=final_output_node),
        Edge(from_node=security_event_handler_node, to_node=final_output_node),
    ],
    description="TechNova Solutions Customer Support Agent Workflow",
)

app = App(
    root_agent=root_agent,
    name="app",
)
