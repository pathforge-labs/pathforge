/**
 * PathForge — Resume API Types
 * ==============================
 * TypeScript interfaces for resume management endpoints.
 */

export interface ResumeSummary {
  id: string;
  title: string;
  version: number;
  raw_text_length: number;
  has_structured_data: boolean;
  has_embedding: boolean;
  created_at: string | null;
}
