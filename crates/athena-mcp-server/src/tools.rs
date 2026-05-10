use serde_json::{json, Value};

#[derive(Debug, Clone)]
pub struct ToolDef {
    pub name: &'static str,
    pub description: &'static str,
    pub input_schema: Value,
}

pub fn all_tools() -> Vec<ToolDef> {
    vec![
        ToolDef {
            name: "athena_run_iteration",
            description: "Run one OODA iteration (Observe → Orient → Decide → Act) for an operation. Returns iteration ID and number of facts collected.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "op_id": {
                        "type": "string",
                        "description": "UUID of the operation (new UUID will be minted if omitted)"
                    }
                },
                "required": []
            }),
        },
        ToolDef {
            name: "athena_list_facts",
            description: "List all facts collected for an operation.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "op_id": { "type": "string", "description": "Operation UUID" }
                },
                "required": ["op_id"]
            }),
        },
        ToolDef {
            name: "athena_c5isr_status",
            description: "Get the 6-domain C5ISR health status (Command, Control, Communications, Computers, Intelligence, Surveillance/Reconnaissance) for an operation.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "op_id": { "type": "string", "description": "Operation UUID" }
                },
                "required": ["op_id"]
            }),
        },
        ToolDef {
            name: "athena_generate_report",
            description: "Generate a structured penetration test report for an operation. Returns findings sorted by severity.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "op_id": { "type": "string", "description": "Operation UUID" },
                    "format": {
                        "type": "string",
                        "enum": ["json", "markdown"],
                        "description": "Output format (default: json)"
                    }
                },
                "required": ["op_id"]
            }),
        },
        ToolDef {
            name: "athena_abort_operation",
            description: "Abort an active OODA loop for an operation.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "op_id": { "type": "string", "description": "Operation UUID" }
                },
                "required": ["op_id"]
            }),
        },
    ]
}

pub fn tools_list_result() -> Value {
    let tools: Vec<Value> = all_tools().iter().map(|t| json!({
        "name": t.name,
        "description": t.description,
        "inputSchema": t.input_schema.clone(),
    })).collect();
    json!({ "tools": tools })
}
