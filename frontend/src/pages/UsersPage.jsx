import { useQuery } from "@tanstack/react-query";
import { ROLE_NAME } from "../auth";
import ListLayout from "../components/ListLayout";
import DataTable from "../components/DataTable";
import SettingsTabs from "../components/SettingsTabs";
import StatusBadge from "../components/StatusBadge";

// is_active → key ของ StatusBadge
const userStatus = (u) => (u.is_active ? "active" : "disabled");

// หน้า /settings/users: GET /users แสดงรายการ, route ลูกเปิด popup เพิ่ม/แก้ผู้ใช้
export default function UsersPage() {
  const { data, error } = useQuery({ queryKey: ["users"] });
  return (
    <ListLayout
      title="ตั้งค่าและผู้ใช้"
      basePath="/settings/users"
      action={{ label: "เพิ่มผู้ใช้", to: "/settings/users/new" }}
      toolbar={<SettingsTabs />}
    >
      {error && (
        <p role="alert" className="field-error">
          {error.message}
        </p>
      )}
      <DataTable
        items={data}
        to={(u) => `/settings/users/${u.id}`}
        empty="ยังไม่มีผู้ใช้"
        card={(u) => (
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="truncate font-semibold">{u.full_name}</div>
              <div className="text-sm text-muted">
                {u.username} · {ROLE_NAME[u.role]}
              </div>
            </div>
            <StatusBadge status={userStatus(u)} />
          </div>
        )}
        columns={[
          { label: "ชื่อผู้ใช้", render: (u) => u.username },
          { label: "ชื่อ", render: (u) => u.full_name },
          { label: "บทบาท", render: (u) => ROLE_NAME[u.role] },
          { label: "สถานะ", render: (u) => <StatusBadge status={userStatus(u)} /> },
        ]}
      />
    </ListLayout>
  );
}
