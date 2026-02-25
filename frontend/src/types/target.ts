export interface Target {
  id: string;
  hostname: string;
  ipAddress: string;
  os: string | null;
  role: string;
  networkSegment: string;
  isCompromised: boolean;
  privilegeLevel: string | null;
  operationId: string;
}
