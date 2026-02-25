import { C5ISRDomain, C5ISRDomainStatus } from "./enums";

export interface C5ISRStatus {
  id: string;
  operationId: string;
  domain: C5ISRDomain;
  status: C5ISRDomainStatus;
  healthPct: number;
  detail: string;
}
