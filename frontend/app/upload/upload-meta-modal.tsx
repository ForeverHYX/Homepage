"use client";

type ModalData = {
  path: string;
  title: string;
  description: string;
  date: string;
  author: string;
};

type UploadMetaModalProps = {
  modalData: ModalData;
  setModalData: React.Dispatch<React.SetStateAction<ModalData>>;
  onSave: () => void;
  onCancel: () => void;
};

export function UploadMetaModal({ modalData, setModalData, onSave, onCancel }: UploadMetaModalProps) {
  return (
    <>
      <h2 style={{ marginTop: 0, fontSize: "18px", color: "var(--heading)" }}>Edit Folder Info</h2>
      <div style={{ marginBottom: "12px" }}>
        <label style={{ display: "block", marginBottom: "4px", fontWeight: 500, color: "var(--text)" }}>Title</label>
        <input value={modalData.title} onChange={(e) => setModalData({ ...modalData, title: e.target.value })} style={{ width: "100%", padding: "8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface)", color: "var(--text)" }} />
      </div>
      <div style={{ marginBottom: "12px" }}>
        <label style={{ display: "block", marginBottom: "4px", fontWeight: 500, color: "var(--text)" }}>Shoot Date</label>
        <input type="date" value={modalData.date} onChange={(e) => setModalData({ ...modalData, date: e.target.value })} style={{ width: "100%", padding: "8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface)", color: "var(--text)" }} />
      </div>
      <div style={{ marginBottom: "12px" }}>
        <label style={{ display: "block", marginBottom: "4px", fontWeight: 500, color: "var(--text)" }}>Author</label>
        <input value={modalData.author} onChange={(e) => setModalData({ ...modalData, author: e.target.value })} style={{ width: "100%", padding: "8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface)", color: "var(--text)" }} placeholder="Yixun Hong" />
      </div>
      <div style={{ marginBottom: "20px" }}>
        <label style={{ display: "block", marginBottom: "4px", fontWeight: 500, color: "var(--text)" }}>Description</label>
        <textarea rows={3} value={modalData.description} onChange={(e) => setModalData({ ...modalData, description: e.target.value })} style={{ width: "100%", padding: "8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface)", color: "var(--text)", fontFamily: "inherit" }} />
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
        <button className="btn" style={{ background: "var(--surface-highlight)", color: "var(--text)" }} onClick={onCancel}>Cancel</button>
        <button className="btn btn-primary" onClick={onSave}>Save</button>
      </div>
    </>
  );
}
