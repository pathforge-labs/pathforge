/**
 * PathForge — FileUpload Component Tests
 * ========================================
 * Validates file upload component behavior: drop zone rendering,
 * validation, callbacks, error states, and file removal.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FileUpload, type FileUploadProps } from "@/components/file-upload";

// ── Test Helpers ───────────────────────────────────────────

function createTestFile(
  name: string,
  size: number,
  type: string,
): File {
  const content = new Array(size).fill("a").join("");
  return new File([content], name, { type });
}

function renderFileUpload(overrides: Partial<FileUploadProps> = {}) {
  const defaultProps: FileUploadProps = {
    onFileSelect: vi.fn(),
    onFileRemove: vi.fn(),
    selectedFile: null,
    isLoading: false,
    error: null,
    ...overrides,
  };

  return {
    ...render(<FileUpload {...defaultProps} />),
    props: defaultProps,
  };
}

// ── Tests ──────────────────────────────────────────────────

describe("FileUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render drop zone with correct accept types", () => {
    renderFileUpload();

    const dropzone = screen.getByTestId("file-upload-dropzone");
    expect(dropzone).toBeDefined();
    expect(screen.getByText(/drag & drop your resume/i)).toBeDefined();
    expect(screen.getByText(/\.txt, \.pdf, \.doc, \.docx/i)).toBeDefined();
  });

  it("should display file info after selection", () => {
    const file = createTestFile("resume.txt", 1024, "text/plain");

    renderFileUpload({ selectedFile: file });

    expect(screen.getByText("resume.txt")).toBeDefined();
    expect(screen.getByText("1.0 KB")).toBeDefined();
  });

  it("should reject files exceeding size limit", () => {
    const onFileSelect = vi.fn();
    renderFileUpload({ onFileSelect });

    // Create a file > 5MB
    const largeFile = createTestFile("big.txt", 6 * 1024 * 1024, "text/plain");

    const input = screen.getByTestId("file-upload-input") as HTMLInputElement;

    // Simulate file selection via input
    Object.defineProperty(input, "files", { value: [largeFile] });
    fireEvent.change(input);

    expect(onFileSelect).not.toHaveBeenCalled();
    expect(screen.getByTestId("file-upload-error")).toBeDefined();
  });

  it("should reject invalid file types", () => {
    const onFileSelect = vi.fn();
    renderFileUpload({ onFileSelect });

    const invalidFile = createTestFile("malware.exe", 100, "application/x-msdownload");

    const input = screen.getByTestId("file-upload-input") as HTMLInputElement;
    Object.defineProperty(input, "files", { value: [invalidFile] });
    fireEvent.change(input);

    expect(onFileSelect).not.toHaveBeenCalled();
    expect(screen.getByTestId("file-upload-error")).toBeDefined();
  });

  it("should call onFileSelect callback with valid file", () => {
    const onFileSelect = vi.fn();
    renderFileUpload({ onFileSelect });

    const validFile = createTestFile("resume.txt", 500, "text/plain");

    const input = screen.getByTestId("file-upload-input") as HTMLInputElement;
    Object.defineProperty(input, "files", { value: [validFile] });
    fireEvent.change(input);

    expect(onFileSelect).toHaveBeenCalledWith(validFile);
  });

  it("should show remove button when file is selected", () => {
    const file = createTestFile("resume.txt", 1024, "text/plain");
    renderFileUpload({ selectedFile: file });

    const removeButton = screen.getByTestId("file-upload-remove");
    expect(removeButton).toBeDefined();
  });

  it("should call onFileRemove on remove click", () => {
    const onFileRemove = vi.fn();
    const file = createTestFile("resume.txt", 1024, "text/plain");
    renderFileUpload({ selectedFile: file, onFileRemove });

    const removeButton = screen.getByTestId("file-upload-remove");
    fireEvent.click(removeButton);

    expect(onFileRemove).toHaveBeenCalledOnce();
  });

  it("should show error message for external errors", () => {
    renderFileUpload({ error: "Upload failed: network error" });

    expect(screen.getByText("Upload failed: network error")).toBeDefined();
  });
});
