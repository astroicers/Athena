import { FactCategory } from "./enums";

export interface Fact {
  id: string;
  trait: string;
  value: string;
  category: FactCategory;
  sourceTechniqueId: string | null;
  sourceTargetId: string | null;
  operationId: string;
  score: number;
  collectedAt: string;
}
