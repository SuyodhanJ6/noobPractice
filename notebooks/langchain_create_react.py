# # from langchain.agents import create_agent
# # from langchain.tools import tool
# # from dotenv import load_dotenv
# # from langchain_openai import ChatOpenAI
# # from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
# # from langchain_core.prompts import PromptTemplate

# # system_prompt = SystemMessage(
# #     content="You are a helpful calculator."
# # )

# # load_dotenv()
# # llm = ChatOpenAI(model="gpt-4o-mini")
# # @tool
# # def add(a: int, b: int) -> int:
# #     "Add two numbers"
# #     return a + b

# # @tool
# # def subtract(a: int, b: int) -> int:
# #     "Subtract two numbers"
# #     return a - b

# # @tool
# # def multiply(a: int, b: int) -> int:
# #     "Multiply two numbers"
# #     return a * b

# # @tool
# # def divide(a: int, b: int) -> float:
# #     "Divide two numbers"
# #     return a / b

# # # add_tool = tool(name="add", func=add, description="Add two numbers")
# # # subtract_tool = tool(name="subtract", func=subtract, description="Subtract two numbers")
# # # multiply_tool = tool(name="multiply", func=multiply, description="Multiply two numbers")
# # # divide_tool = tool(name="divide", func=divide, description="Divide two numbers")

# # agent = create_agent(llm,
# # tools=[add, subtract, multiply, divide],
# # system_prompt=system_prompt.content,
# # debug=True,
# # )
# # from IPython.display import display
# # display(agent.get_graph().draw_mermaid_png())

# # result = agent.invoke({"messages": [HumanMessage(content="What is 10 + 20?")]})
# # # print(result["messages"][-1])



# # print(result["messages"][-1].content)



# from langchain.agents import create_agent
# from langchain.tools import tool
# from dotenv import load_dotenv
# from langchain_openai import ChatOpenAI
# from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
# from langchain_core.prompts import PromptTemplate

# from langchain.agents.middleware import (
#     PIIMiddleware,
#     SummarizationMiddleware,
#     HumanInTheLoopMiddleware
# )

# system_prompt = SystemMessage(
#     content="You are a helpful calculator."
# )

# load_dotenv()
# llm = ChatOpenAI(model="gpt-4o-mini")
# @tool
# def add(a: int, b: int) -> int:
#     "Add two numbers"
#     return a + b

# @tool
# def subtract(a: int, b: int) -> int:
#     "Subtract two numbers"
#     return a - b

# @tool
# def multiply(a: int, b: int) -> int:
#     "Multiply two numbers"
#     return a * b

# @tool
# def divide(a: int, b: int) -> float:
#     "Divide two numbers"
#     return a / b


# system_prompt = SystemMessage(content="You are a helpful assistant that can answer questions only reated to calculator and help with tasks.")

# agent = create_agent(
#     llm,
#     tools=[add, subtract, multiply, divide],
#     system_prompt=system_prompt.content,
#     debug=True,
#     middleware=[
#         # PIIMiddleware: Not strictly necessary for calculator, but good for general safety
#         # You can customize patterns or remove this if not needed
#         # PIIMiddleware("credit_card", strategy="mask"),
#         # PIIMiddleware("url", strategy="redact"),
#         # PIIMiddleware("ip", strategy="hash"),
        
#         # SummarizationMiddleware: Useful for long calculation sessions
#         SummarizationMiddleware(
#             model=llm,
#             max_tokens_before_summary=800  # Higher threshold since calculator conversations are usually shorter
#         ),
        
#         # HumanInTheLoopMiddleware: Customized for your divide tool to prevent division by zero
#         # or handle potentially problematic calculations
#         HumanInTheLoopMiddleware(
#             interrupt_on={
#                 "divide": {
#                     "allowed_decisions": ["approve", "edit", "reject"],
#                     "message": "Confirm division operation - check if divisor is zero"
#                 }
#             }
#         ),
#     ]
# )  



# def handle_agent_with_interrupts(query):
#     """Handle agent invocation with proper interrupt handling"""
#     initial_state = {"messages": [HumanMessage(content=query)]}
    
#     # First, try to get the initial result
#     result = agent.invoke(initial_state)
    
#     # Check if there's an interrupt
#     while result.get("__interrupt__"):
#         interrupt_data = result["__interrupt__"]
        
#         # Extract action requests from interrupt
#         if isinstance(interrupt_data, list) and len(interrupt_data) > 0:
#             interrupt_obj = interrupt_data[0]
#             if hasattr(interrupt_obj, 'value'):
#                 interrupt_value = interrupt_obj.value
#             else:
#                 interrupt_value = interrupt_obj
#         else:
#             interrupt_value = interrupt_data[0].value if hasattr(interrupt_data[0], 'value') else interrupt_data[0]
            
#         action_requests = interrupt_value["action_requests"]
#         print(f"🚨 Human approval needed for: {action_requests}")
        
#         # Handle each interrupt - wait for actual human input
#         interrupts = []
#         for request in action_requests:
#             action_name = request["name"]
#             args = request["args"]
            
#             print(f"\n🔍 Tool: {action_name}")
#             print(f"📋 Arguments: {args}")
#             print(f"📝 Description: {request.get('description', 'No description provided')}")
            
#             # Get human decision
#             while True:
#                 decision = input(f"\n🤔 What do you want to do with {action_name}? (approve/edit/reject): ").strip().lower()
#                 if decision in ["approve", "edit", "reject"]:
#                     break
#                 print("❌ Please enter: approve, edit, or reject")
            
#             if decision == "approve":
#                 print(f"✅ Approving {action_name} with args: {args}")
#                 interrupts.append({
#                     "action_name": action_name,
#                     "decision": "approve"
#                 })
#             elif decision == "edit":
#                 print(f"✏️  Editing {action_name} - you can modify the arguments")
#                 print("Current args:", args)
#                 new_args = input("Enter new args (JSON format) or press Enter to keep current: ").strip()
#                 if new_args:
#                     try:
#                         import json
#                         edited_args = json.loads(new_args)
#                         print(f"✅ Editing {action_name} with new args: {edited_args}")
#                         interrupts.append({
#                             "action_name": action_name,
#                             "decision": "edit",
#                             "edited_args": edited_args
#                         })
#                     except:
#                         print("❌ Invalid JSON, using original args")
#                         interrupts.append({
#                             "action_name": action_name,
#                             "decision": "approve"
#                         })
#                 else:
#                     interrupts.append({
#                         "action_name": action_name,
#                         "decision": "approve"
#                     })
#             else:  # reject
#                 print(f"❌ Rejecting {action_name}")
#                 interrupts.append({
#                     "action_name": action_name,
#                     "decision": "reject"
#                 })
        
#         print("🔄 Continuing execution with your decision...")
        
#         # Continue with the interrupts - use the current state and provide interrupts
#         # The key is to pass the current messages and interrupts together
#         continue_state = {
#             "messages": result.get("messages", initial_state["messages"]),
#             "interrupts": interrupts
#         }
        
#         # Get the next result with interrupt decisions
#         result = agent.invoke(continue_state)
        
#         # If we still have an interrupt, we'll handle it in the next iteration
        
#     return result

# # Test the middleware
# result = handle_agent_with_interrupts("what is 10 devide by 5")

# print("\n" + "="*50)
# print("FINAL RESULTS:")
# print("="*50)

# if result.get("messages") and len(result["messages"]) > 0:
#     # Look for the last message with content
#     messages = result["messages"]
#     final_content = None
    
#     # Go through messages in reverse to find the last one with content
#     for msg in reversed(messages):
#         if hasattr(msg, 'content') and msg.content and msg.content.strip():
#             final_content = msg.content
#             break
    
#     if final_content:
#         print(f"✅ Final result: {final_content}")
#     else:
#         print("⚠️  No content found in messages")
#         print(f"📋 Message count: {len(messages)}")
#         print(f"📋 Last message type: {type(messages[-1]) if messages else 'None'}")
#         if messages:
#             print(f"📋 Last message attributes: {dir(messages[-1])}")
# else:
#     print("❌ No messages found in result")
#     print(f"🔍 Result keys: {result.keys()}")
    
#     # Check if there are any tool results we can extract
#     if result.get("__interrupt__"):
#         print("🔄 Result still has interrupt - this might be expected")