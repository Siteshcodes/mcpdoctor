from pydantic import Field # Used to describe tool parameters (add descriptions, defaults, validation)

from mcp.server.fastmcp import FastMCP # High-level MCP server framework — handles the protocol plumbing for you

from mcp.server.fastmcp.prompts import base


# Create the MCP server instance.
# "DocumentMCP" is the server's name, shown to clients when they connect.
# log_level="ERROR" keeps the console quiet — only errors get logged, not info/debug noise.
mcp = FastMCP("DocumentMCP", log_level="ERROR")


# In-memory "database" of documents — stands in for a real datastore while you build/test.
# Keys   = filenames (the ID a client uses to look up a doc)
# Values = the document's contents/summary
docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}
# Register this function as an MCP tool the LLM can call.
# name        = the identifier the client/LLM uses to invoke it
# description = tells the LLM what the tool does, so it knows WHEN to call it
@mcp.tool(
    name = "read_doc_content",
    description="Read content from document and return as a string."
)
def read_document(
    # Field description explains this parameter to the LLM,
    # so it knows what value to pass when calling the tool.
    doc_id: str = Field(description = "Id of the document to read")
):
    # Guard clause: if the requested doc doesn't exist, fail loudly
    # instead of returning None or a confusing error later.
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")
    
    # Hand back the document's contents to the caller.
    return docs[doc_id]


# Second tool: lets the LLM modify a document's contents.
@mcp.tool(
    name ="edit_doc",
    description ="Edit a document by replacing a string in the document content with the new string "
)
def edit_document(
    doc_id: str = Field(description = "Id of the document that willbe edited"),
    old_str: str = Field(description = "The text to replace.Must match exactly,including whitespace"),
    new_str: str = Field(description = "The new text to insert in place of the old text.") 
):
    # Same existence check as above — don't try to edit a doc that isn't there.
    if doc_id not in docs:
        raise ValueError(f"Doc with {doc_id} not found")
    
    # Find old_str in the document and swap it for new_str.
    # Note: .replace() swaps EVERY occurrence, not just the first one.
    docs[doc_id] = docs[doc_id].replace(old_str , new_str)


# TODO: Write a resource to return all doc id's

# @mcp.resource registers a READ-ONLY data endpoint (not a tool the LLM invokes).
# Clients fetch it by its URI. Use resources for "here's some data" and
# tools for "do something / take an action".
@mcp.resource(
    "docs://documents",          # the URI the client uses to request this resource
    mime_type = "application/json" #hint to client what kind the data we return 
)
def list_docs() -> list[str]:
    # Return just the filenames (the keys), not the contents —
    # this is the "index" a client reads to see what docs exist.
    return list(docs.keys())

# TODO: Write a resource to return the contents of a particular doc

#The {doc_id} in the URI makes this a resource TEMPLATE — the client fills in
# that slot (e.g. docs://documents/plan.md) and it gets passed as the doc_id arg.
@mcp.resource(
    "docs://documents/{doc_id}",
    mime_type = "text/plain"                 # returning raw document text, so plain text
)
def fetch_doc(doc_id: str) -> str:
        # Existence check before we try to look it up.
    if doc_id not in docs:
        return ValueError(f"Doc with id{doc_id} id not found") 
    
    return docs[doc_id]




# TODO: Write a prompt to rewrite a doc in markdown format

@mcp.prompt(
    name ="format_document",
    description ="Rewrite the contents of the document in markdown format."
)
def format_document(
    doc_id : str=Field(description= "Id of the document to format")
) -> list[base.Message]:
    prompt = f"""
Your goal is to reformat a document so it's written using proper markdown syntax.

The id of the document you need to reformat is:
<document_id>
{doc_id}
</document_id>

Follow these steps in order:
1. Use the 'read_doc_content' tool to read the document's current contents.
2. Rewrite the content using markdown — add headers, bullet points, numbered lists, tables, and bold/italic emphasis wherever they make the document clearer and better structured.
3. Use the 'edit_document' tool to apply your changes. You may call it more than once to reformat different sections.

Important constraints:
- Only change the formatting. Do not add, remove, or reword the actual information in the document.
- When calling 'edit_document', 'old_str' must match the existing text exactly, including whitespace — otherwise the replacement will silently do nothing.

Once the document has been fully reformatted, give a short summary of the changes you made.
"""
    return [
        base.UserMessage(prompt)
    ]





# TODO: Write a prompt to summarize a doc


if __name__ == "__main__":
    mcp.run(transport="stdio")
