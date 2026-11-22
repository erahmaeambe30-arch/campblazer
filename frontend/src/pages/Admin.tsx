import { useEffect, useRef, useState, type FormEvent } from "react";
import { FiCamera, FiDatabase, FiEdit2, FiImage, FiPlus, FiStar, FiTrash2, FiX } from "react-icons/fi";
import { Spinner } from "../components/Cards";
import { countByStatus, ReservationList, StatusTabs } from "../components/Reservations";
import { SlotManager } from "../components/SlotManager";
import { api, upload, mediaUrl } from "../lib/api";
import { peso, roleLabel } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useLiveEvent } from "../lib/realtime";
import type { Reservation, User } from "../lib/types";

type AdminDest = {
  id: number; name: string; slug: string; category: "BEACH" | "MOUNTAIN"; municipality: string; barangay: string;
  location_verified: boolean; location_note: string; short_description: string; description: string;
  amenities: string[]; activities: string[]; reservation_instructions: string; source_notes: string;
  is_published: boolean; is_verified: boolean; booking_enabled: boolean; is_featured: boolean; is_bookable: boolean;
  cover_image: { url: string; credit: string; caption: string } | null; photo_count: number;
};
type AdminPhoto = { id: number; src: string; credit_line: string; caption: string; is_cover: boolean; stored_in_database: boolean };
const MAX_PHOTO_MB = 5;
type AdminUser = User & { is_active: boolean };
type Svc = Record<string, unknown> & { id: number; destination: number; destination_name: string; is_verified: boolean; is_active: boolean; is_demo: boolean };

const TABS = ["Overview", "Destinations", "Services", "Availability", "Reservations", "Users"] as const;
const MUNIS = ["Almeria", "Biliran", "Cabucgayan", "Caibiran", "Culaba", "Kawayan", "Maripipi", "Naval"];

export default function Admin() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  return (
    <div className="page container dash">
      <div className="dash-head"><div><span className="eyebrow">System administrator</span><h1>Admin dashboard</h1></div></div>
      <div className="seg seg-wrap admin-tabs">{TABS.map((t) => <button key={t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>{t}</button>)}</div>
      {tab === "Overview" && <Overview />}
      {tab === "Destinations" && <Destinations />}
      {tab === "Services" && <Services />}
      {tab === "Availability" && <section className="panel"><h3>Availability &amp; schedules (all services)</h3><SlotManager /></section>}
      {tab === "Reservations" && <AllReservations />}
      {tab === "Users" && <Users />}
    </div>
  );
}

function Overview() {
  const { data } = useApi<Record<string, any>>("/admin/stats/"); // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!data) return <Spinner />;
  const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);
  const cards: [string, string | number][] = [
    ["Registered users", data.users], ["Destinations", `${data.destinations.total} (${data.destinations.beaches} beach · ${data.destinations.mountains} mountain)`],
    ["Verified destinations", data.destinations.verified], ["Booking-enabled", data.destinations.bookable],
    ["Beach venues", data.venues], ["Mountain guides", data.guides],
    ["Open venue slots", data.open_venue_slots], ["Open guide schedules", data.open_guide_schedules],
    ["Beach reservations", sum(data.beach_reservations)], ["Guide reservations", sum(data.guide_reservations)],
    ["Simulated booking value", peso(data.simulated_booking_value_php)],
  ];
  return (
    <div className="stat-grid">
      {cards.map(([l, v]) => <div key={l} className="stat-card"><span>{l}</span><b>{v}</b></div>)}
      <div className="stat-card wide"><span>Reservations by status</span>
        <p className="small">Beach: {JSON.stringify(data.beach_reservations)} · Mountain: {JSON.stringify(data.guide_reservations)}</p></div>
    </div>
  );
}

function Destinations() {
  const { data, reload } = useApi<AdminDest[]>("/admin/destinations/");
  const [edit, setEdit] = useState<{ d: Partial<AdminDest>; photos?: boolean } | null>(null);
  const [msg, setMsg] = useState("");
  const patch = async (d: AdminDest, body: Partial<AdminDest>) => {
    setMsg("");
    try { await api(`/admin/destinations/${d.id}/`, { method: "PATCH", body }); reload(); }
    catch (x) { setMsg(`${d.name}: ${(x as Error).message}`); }
  };
  const remove = async (d: AdminDest) => {
    if (!confirm(`Delete ${d.name}? This cannot be undone.`)) return;
    try { await api(`/admin/destinations/${d.id}/`, { method: "DELETE" }); reload(); } catch (x) { setMsg((x as Error).message); }
  };
  return (
    <section className="panel">
      <div className="panel-head"><h3>Destinations (Biliran only)</h3><button className="pill pill-solid pill-sm" onClick={() => setEdit({ d: { category: "BEACH", amenities: [], activities: [], is_published: true } })}><FiPlus /> Add destination</button></div>
      {msg && <div className="result result-err">{msg}</div>}
      {!data ? <Spinner /> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Photo</th><th>Name</th><th>Type</th><th>Municipality</th><th>Location ✓</th><th>Verified</th><th>Bookings</th><th>Featured</th><th></th></tr></thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.id}>
                  <td>
                    <button className="photo-cell" onClick={() => setEdit({ d, photos: true })} title="Manage photos">
                      {d.cover_image ? <img src={mediaUrl(d.cover_image.url)} alt="" /> : <span><FiCamera /></span>}
                      <small>{d.photo_count}</small>
                    </button>
                  </td>
                  <td><a href={`#/destinations/${d.slug}`}>{d.name}</a></td>
                  <td>{d.category === "BEACH" ? "Beach" : "Mountain"}</td>
                  <td>{d.municipality || <span className="muted">pending</span>}</td>
                  <td><Toggle on={d.location_verified} set={(v) => patch(d, { location_verified: v })} /></td>
                  <td><Toggle on={d.is_verified} set={(v) => patch(d, v ? { is_verified: true } : { is_verified: false, booking_enabled: false })} /></td>
                  <td><Toggle on={d.booking_enabled} set={(v) => patch(d, { booking_enabled: v })} /></td>
                  <td><Toggle on={d.is_featured} set={(v) => patch(d, { is_featured: v })} /></td>
                  <td className="row-actions"><button className="icon-btn" title="Photos" onClick={() => setEdit({ d, photos: true })}><FiImage /></button><button className="icon-btn" title="Edit" onClick={() => setEdit({ d })}><FiEdit2 /></button><button className="icon-btn" onClick={() => remove(d)}><FiTrash2 /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {edit && <DestinationEditor d={edit.d} focusPhotos={!!edit.photos} close={() => { setEdit(null); reload(); }} changed={reload} />}
    </section>
  );
}

function Toggle({ on, set }: { on: boolean; set: (v: boolean) => void }) {
  return <button className={`toggle ${on ? "on" : ""}`} onClick={() => set(!on)} aria-pressed={on}><span /></button>;
}

function DestinationEditor({ d, focusPhotos, close, changed }: { d: Partial<AdminDest>; focusPhotos: boolean; close: () => void; changed: () => void }) {
  const [v, setV] = useState<Partial<AdminDest>>(d);
  const [id, setId] = useState<number | undefined>(d.id); // set right after a NEW destination is saved
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  // Photo chosen directly in the "New destination" form (uploaded right after the destination is created).
  const [newPhoto, setNewPhoto] = useState<File | null>(null);
  const [newPhotoCredit, setNewPhotoCredit] = useState("");
  const [newPreview, setNewPreview] = useState<string | null>(null);
  const photosRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!newPhoto) { setNewPreview(null); return; }
    const url = URL.createObjectURL(newPhoto);
    setNewPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [newPhoto]);
  const pickNew = (f: File | null) => {
    setErr("");
    if (f && !["image/jpeg", "image/png", "image/webp"].includes(f.type)) { setErr("Choose a JPG, PNG or WEBP photo."); return; }
    if (f && f.size > MAX_PHOTO_MB * 1024 * 1024) { setErr(`Photo is ${(f.size / 1048576).toFixed(1)} MB. The limit is ${MAX_PHOTO_MB} MB.`); return; }
    setNewPhoto(f);
  };
  const s = (k: keyof AdminDest) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const list = (k: "amenities" | "activities") => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) });

  useEffect(() => {
    if (focusPhotos && id) photosRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [focusPhotos, id]);

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setErr(""); setNote("");
    if (!id && newPhoto && !newPhotoCredit.trim()) { setErr("Add a photo credit (who took the photo)."); return; }
    const body = { name: v.name, category: v.category, municipality: v.municipality ?? "", barangay: v.barangay ?? "", location_note: v.location_note ?? "",
      short_description: v.short_description, description: v.description ?? "", amenities: v.amenities ?? [], activities: v.activities ?? [],
      reservation_instructions: v.reservation_instructions ?? "", source_notes: v.source_notes ?? "" };
    setBusy(true);
    try {
      const saved = await api<AdminDest>(id ? `/admin/destinations/${id}/` : "/admin/destinations/", { method: id ? "PATCH" : "POST", body });
      if (!id) {
        setId(saved.id); setV(saved);
        let msg = "Destination saved to the database.";
        if (newPhoto) {
          const form = new FormData();
          form.append("destination", String(saved.id));
          form.append("image_file", newPhoto);
          form.append("credit", newPhotoCredit.trim());
          form.append("is_cover", "true");
          try { await upload("/admin/images/", form); msg += " Cover photo uploaded."; setNewPhoto(null); }
          catch (x) { msg += ` Photo upload failed: ${(x as Error).message} — try again below.`; }
        }
        changed();
        // Keep the drawer open so more photos can be added straight away.
        setNote(msg + " You can add more photos below.");
        setTimeout(() => photosRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
      } else { changed(); close(); }
    } catch (x) { setErr((x as Error).message); }
    finally { setBusy(false); }
  };

  return (
    <div className="drawer" role="dialog">
      <div className="drawer-card">
        <div className="panel-head"><h3>{id ? `Edit ${v.name ?? ""}` : "New destination"}</h3><button className="icon-btn" onClick={close}><FiX /></button></div>
        <form onSubmit={submit} className="stack">
          <div className="grid-2">
            <label>Name<input required value={v.name ?? ""} onChange={s("name")} /></label>
            <label>Category<select value={v.category} onChange={s("category")} disabled={!!id}><option value="BEACH">Beach (venue booking)</option><option value="MOUNTAIN">Mountain (tour guides)</option></select></label>
          </div>
          <div className="grid-2">
            <label>Municipality (Biliran)<select value={v.municipality ?? ""} onChange={s("municipality")}><option value="">— not yet verified —</option>{MUNIS.map((m) => <option key={m}>{m}</option>)}</select></label>
            <label>Barangay<input value={v.barangay ?? ""} onChange={s("barangay")} /></label>
          </div>
          <label>Location note<input value={v.location_note ?? ""} onChange={s("location_note")} /></label>
          <label>Short description<input required maxLength={280} value={v.short_description ?? ""} onChange={s("short_description")} /></label>
          <label>Description<textarea rows={3} value={v.description ?? ""} onChange={s("description")} /></label>
          <label>Amenities (comma-separated, verified only)<input value={(v.amenities ?? []).join(", ")} onChange={list("amenities")} /></label>
          <label>Activities (comma-separated)<input value={(v.activities ?? []).join(", ")} onChange={list("activities")} /></label>
          <label>Reservation instructions<textarea rows={2} value={v.reservation_instructions ?? ""} onChange={s("reservation_instructions")} /></label>
          <label>Source notes (admin only)<textarea rows={2} value={v.source_notes ?? ""} onChange={s("source_notes")} /></label>
          {!id && (
            <>
              <label className="dropzone">
                {newPreview ? <img src={newPreview} alt="Preview" /> : <span><FiCamera /> Cover photo (JPG, PNG or WEBP, max {MAX_PHOTO_MB} MB)</span>}
                <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => pickNew(e.target.files?.[0] ?? null)} />
              </label>
              {newPhoto && <label>Photo credit (required)<input required value={newPhotoCredit} onChange={(e) => setNewPhotoCredit(e.target.value)} placeholder="e.g. Own photo · Photo by J. Cruz" /></label>}
            </>
          )}
          {err && <div className="result result-err">{err}</div>}
          {note && <div className="result result-ok">{note}</div>}
          <button className="pill pill-solid" disabled={busy}>{busy ? "Saving…" : id ? "Save changes" : newPhoto ? "Save destination + photo" : "Save destination"}</button>
        </form>
        <div ref={photosRef}>
          {id ? <PhotoManager destinationId={id} changed={changed} />
            : null}
        </div>
      </div>
    </div>
  );
}

/** Upload / list / delete / set-cover for one destination's photos.
 *  Uploaded files are stored in PostgreSQL by the server (not on its disk). */
function PhotoManager({ destinationId, changed }: { destinationId: number; changed: () => void }) {
  const photos = useApi<AdminPhoto[]>(`/admin/images/?destination=${destinationId}`);
  const empty = { image_url: "", credit: "", license: "", caption: "", is_cover: false };
  const [ph, setPh] = useState(empty);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const pick = (f: File | null) => {
    setErr(""); setOk("");
    if (f && !["image/jpeg", "image/png", "image/webp"].includes(f.type)) { setErr("Choose a JPG, PNG or WEBP photo."); return; }
    if (f && f.size > MAX_PHOTO_MB * 1024 * 1024) { setErr(`Photo is ${(f.size / 1048576).toFixed(1)} MB. The limit is ${MAX_PHOTO_MB} MB.`); return; }
    setFile(f);
  };
  const refresh = () => { photos.reload(); changed(); };

  const addPhoto = async (e: FormEvent) => {
    e.preventDefault(); setErr(""); setOk("");
    if (!file && !ph.image_url) { setErr("Choose a photo file (or paste an https:// image link)."); return; }
    const form = new FormData();
    form.append("destination", String(destinationId));
    form.append("credit", ph.credit); form.append("license", ph.license); form.append("caption", ph.caption);
    form.append("is_cover", ph.is_cover || (photos.data?.length ?? 0) === 0 ? "true" : "false"); // first photo becomes the cover
    if (file) form.append("image_file", file); else form.append("image_url", ph.image_url);
    setBusy(true);
    try {
      await upload("/admin/images/", form);
      setPh(empty); setFile(null); if (fileInput.current) fileInput.current.value = "";
      setOk("Photo saved to the database."); refresh();
    } catch (x) { setErr((x as Error).message); }
    finally { setBusy(false); }
  };
  const makeCover = async (p: AdminPhoto) => { try { await api(`/admin/images/${p.id}/`, { method: "PATCH", body: { is_cover: true } }); refresh(); } catch (x) { setErr((x as Error).message); } };
  const remove = async (p: AdminPhoto) => {
    if (!confirm("Delete this photo from the database?")) return;
    try { await api(`/admin/images/${p.id}/`, { method: "DELETE" }); refresh(); } catch (x) { setErr((x as Error).message); }
  };

  return (
    <section className="photo-manager">
      <h4 className="mt"><FiImage /> Photos <span className="muted small">— authentic, licensed photos only, with credit</span></h4>
      {photos.loading && !photos.data ? <Spinner /> : (
        <div className="thumbs">
          {photos.data?.map((p) => (
            <figure key={p.id} className={p.is_cover ? "is-cover" : ""}>
              <img src={mediaUrl(p.src)} alt={p.caption} />
              <figcaption>{p.is_cover && <b>★ Cover · </b>}{p.stored_in_database && <span title="Stored in PostgreSQL"><FiDatabase /> </span>}{p.credit_line}</figcaption>
              {!p.is_cover && <button type="button" className="icon-btn cover-btn" title="Set as cover" onClick={() => makeCover(p)}><FiStar /></button>}
              <button type="button" className="icon-btn" title="Delete" onClick={() => remove(p)}><FiTrash2 /></button>
            </figure>
          ))}
          {photos.data?.length === 0 && <p className="muted small">No photos yet.</p>}
        </div>
      )}
      <form onSubmit={addPhoto} className="stack">
        <label className="dropzone">
          {preview ? <img src={preview} alt="Preview" /> : <span><FiCamera /> Choose a photo (JPG, PNG or WEBP, max {MAX_PHOTO_MB} MB)</span>}
          <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => pick(e.target.files?.[0] ?? null)} />
        </label>
        {file && <p className="small muted">{file.name} · {(file.size / 1024).toFixed(0)} KB <button type="button" className="link-btn" onClick={() => { setFile(null); if (fileInput.current) fileInput.current.value = ""; }}>remove</button></p>}
        {!file && <label>…or an https:// image link (e.g. Wikimedia Commons)<input type="url" value={ph.image_url} onChange={(e) => setPh({ ...ph, image_url: e.target.value })} /></label>}
        <div className="grid-2">
          <label>Credit (required)<input required value={ph.credit} onChange={(e) => setPh({ ...ph, credit: e.target.value })} placeholder="e.g. Photo by J. Cruz (BiPSU)" /></label>
          <label>Licence / permission<input value={ph.license} onChange={(e) => setPh({ ...ph, license: e.target.value })} placeholder="Own photo · CC BY-SA 4.0 · Used with permission" /></label>
        </div>
        <label>Caption<input value={ph.caption} onChange={(e) => setPh({ ...ph, caption: e.target.value })} /></label>
        <label className="check"><input type="checkbox" checked={ph.is_cover} onChange={(e) => setPh({ ...ph, is_cover: e.target.checked })} /> Use as cover photo</label>
        {err && <div className="result result-err">{err}</div>}
        {ok && <div className="result result-ok">{ok}</div>}
        <button className="pill pill-solid" disabled={busy}>{busy ? "Uploading…" : "Upload photo"}</button>
      </form>
    </section>
  );
}

function Services() {
  const venues = useApi<Svc[]>("/admin/venues/");
  const guides = useApi<Svc[]>("/admin/guides/");
  const dests = useApi<AdminDest[]>("/admin/destinations/");
  const users = useApi<AdminUser[]>("/admin/users/");
  const [kind, setKind] = useState<"venue" | "guide">("venue");
  const [f, setF] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  const create = async (e: FormEvent) => {
    e.preventDefault(); setMsg("");
    const owner = f.owner ? Number(f.owner) : null;
    const body = kind === "venue"
      ? { destination: Number(f.destination), name: f.name, description: f.description ?? "", operator: owner, max_guests: Number(f.max || 10), base_price: f.price, included_guests: Number(f.included || 1), price_per_extra_guest: f.extra || "0", is_verified: false }
      : { destination: Number(f.destination), display_name: f.name, bio: f.description ?? "", user: owner, max_participants: Number(f.max || 8), price_per_group: f.price, price_per_participant: f.extra || "0", accreditation: f.accreditation ?? "", is_verified: false };
    try { await api(`/admin/${kind === "venue" ? "venues" : "guides"}/`, { method: "POST", body }); setF({}); setMsg("Created — verify it below once the operator/guide details are confirmed."); venues.reload(); guides.reload(); }
    catch (x) { setMsg((x as Error).message); }
  };
  const patch = async (path: string, id: number, body: Record<string, unknown>) => {
    try { await api(`/admin/${path}/${id}/`, { method: "PATCH", body }); venues.reload(); guides.reload(); } catch (x) { setMsg((x as Error).message); }
  };
  const del = async (path: string, id: number) => {
    if (!confirm("Delete this service? Services with reservations cannot be deleted.")) return;
    try { await api(`/admin/${path}/${id}/`, { method: "DELETE" }); venues.reload(); guides.reload(); } catch (x) { setMsg((x as Error).message); }
  };
  const destOpts = (dests.data ?? []).filter((d) => d.category === (kind === "venue" ? "BEACH" : "MOUNTAIN"));
  const ownerOpts = (users.data ?? []).filter((u) => u.role === (kind === "venue" ? "VENUE_OPERATOR" : "GUIDE"));

  const table = (title: string, path: string, rows: Svc[] | null, nameKey: string, priceKey: string) => (
    <>
      <h4 className="mt">{title}</h4>
      <div className="table-wrap"><table className="table">
        <thead><tr><th>Name</th><th>Destination</th><th>Price</th><th>Verified</th><th>Active</th><th></th></tr></thead>
        <tbody>
          {(rows ?? []).map((r) => (
            <tr key={r.id}>
              <td>{String(r[nameKey])}{r.is_demo && <span className="demo-pill">Demo</span>}</td><td>{r.destination_name}</td><td>{peso(String(r[priceKey]))}</td>
              <td><Toggle on={r.is_verified} set={(v) => patch(path, r.id, { is_verified: v })} /></td>
              <td><Toggle on={r.is_active} set={(v) => patch(path, r.id, { is_active: v })} /></td>
              <td><button className="icon-btn" onClick={() => del(path, r.id)}><FiTrash2 /></button></td>
            </tr>
          ))}
          {rows?.length === 0 && <tr><td colSpan={6} className="muted">None configured.</td></tr>}
        </tbody>
      </table></div>
    </>
  );

  return (
    <section className="panel">
      <h3>Beach venues &amp; mountain guides</h3>
      <p className="muted small">Only add services with confirmed operator/guide details and prices. Nothing becomes bookable until both the service and its destination are verified and bookings are enabled.</p>
      <form className="slot-form" onSubmit={create}>
        <label>Type<select value={kind} onChange={(e) => { setKind(e.target.value as "venue" | "guide"); setF({}); }}><option value="venue">Beach venue</option><option value="guide">Mountain guide</option></select></label>
        <label>Destination<select required value={f.destination ?? ""} onChange={set("destination")}><option value="">Select…</option>{destOpts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
        <label>{kind === "venue" ? "Venue name" : "Guide / team name"}<input required value={f.name ?? ""} onChange={set("name")} /></label>
        <label>{kind === "venue" ? "Operator account" : "Guide account"}<select value={f.owner ?? ""} onChange={set("owner")}><option value="">(none)</option>{ownerOpts.map((u) => <option key={u.id} value={u.id}>{u.username}</option>)}</select></label>
        <label>{kind === "venue" ? "Base price / slot (₱)" : "Guide fee / group (₱)"}<input required type="number" min="0" step="0.01" value={f.price ?? ""} onChange={set("price")} /></label>
        <label>{kind === "venue" ? "Extra guest fee (₱)" : "Per participant (₱)"}<input type="number" min="0" step="0.01" value={f.extra ?? ""} onChange={set("extra")} /></label>
        <label>{kind === "venue" ? "Max guests" : "Max participants"}<input type="number" min="1" value={f.max ?? ""} onChange={set("max")} /></label>
        {kind === "venue" ? <label>Guests included<input type="number" min="1" value={f.included ?? ""} onChange={set("included")} /></label>
          : <label>Accreditation<input value={f.accreditation ?? ""} onChange={set("accreditation")} /></label>}
        <button className="pill pill-solid">Create</button>
      </form>
      {msg && <p className="small muted">{msg}</p>}
      {table("Beach venues", "venues", venues.data, "name", "base_price")}
      {table("Mountain guides", "guides", guides.data, "display_name", "price_per_group")}
    </section>
  );
}

function AllReservations() {
  const { data, loading, reload } = useApi<Reservation[]>("/admin/reservations/");
  const [tab, setTab] = useState("ALL");
  useLiveEvent(["reservation.new", "reservation.status"], reload);
  const list = data ?? [];
  return (
    <section className="panel">
      <h3>All reservations</h3>
      <StatusTabs value={tab} onChange={setTab} counts={countByStatus(list)} />
      {loading && !data ? <Spinner /> : <ReservationList items={tab === "ALL" ? list : list.filter((r) => r.status === tab)} mode="admin" onChanged={reload} />}
    </section>
  );
}

function Users() {
  const { data, reload } = useApi<AdminUser[]>("/admin/users/");
  const [msg, setMsg] = useState("");
  const patch = async (u: AdminUser, body: Record<string, unknown>) => {
    try { await api(`/admin/users/${u.id}/`, { method: "PATCH", body }); reload(); } catch (x) { setMsg((x as Error).message); }
  };
  return (
    <section className="panel">
      <h3>Users &amp; roles</h3>
      {msg && <div className="result result-err">{msg}</div>}
      {!data ? <Spinner /> : (
        <div className="table-wrap"><table className="table">
          <thead><tr><th>Username</th><th>Name</th><th>Email</th><th>Role</th><th>Active</th></tr></thead>
          <tbody>{data.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td><td>{u.first_name} {u.last_name}</td><td>{u.email}</td>
              <td><select value={u.role} onChange={(e) => patch(u, { role: e.target.value })}>{Object.entries(roleLabel).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></td>
              <td><Toggle on={u.is_active} set={(v) => patch(u, { is_active: v })} /></td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </section>
  );
}
