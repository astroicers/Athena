import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DataTable, Column } from "@/components/data/DataTable";

interface Row {
  id: string;
  name: string;
  status: string;
  [key: string]: unknown;
}

const columns: Column<Row>[] = [
  { key: "name", header: "Name", sortable: true },
  { key: "status", header: "Status" },
];

const data: Row[] = [
  { id: "1", name: "Alpha", status: "active" },
  { id: "2", name: "Bravo", status: "completed" },
  { id: "3", name: "Charlie", status: "active" },
];

describe("DataTable", () => {
  it("renders correct number of rows", () => {
    render(<DataTable columns={columns} data={data} keyField="id" />);
    const rows = screen.getAllByRole("row");
    // 1 header row + 3 data rows
    expect(rows).toHaveLength(4);
  });

  it("shows empty message when data is empty", () => {
    render(
      <DataTable columns={columns} data={[]} keyField="id" emptyMessage="No ops found" />,
    );
    expect(screen.getByText("No ops found")).toBeInTheDocument();
  });

  it("toggles sort indicator on click", () => {
    render(<DataTable columns={columns} data={data} keyField="id" />);
    const nameHeader = screen.getByText("Name");
    fireEvent.click(nameHeader);
    expect(screen.getByText("▲")).toBeInTheDocument();
    fireEvent.click(nameHeader);
    expect(screen.getByText("▼")).toBeInTheDocument();
  });
});
