export interface ApiError {
  status: number;
  detail: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface TopologyNode {
  id: string;
  label: string;
  type: string;
  x?: number;
  y?: number;
  data: Record<string, unknown>;
}

export interface TopologyEdge {
  source: string;
  target: string;
  label?: string;
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface WebSocketEvent {
  event: string;
  data: unknown;
  timestamp: string;
}
