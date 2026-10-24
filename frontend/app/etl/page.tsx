import { ComingSoon } from "@/components/ComingSoon";

export default function EtlPage() {
  return (
    <ComingSoon title="Tab ETL đang được xây dựng">
      Tab này sẽ hiển thị quá trình Spark xử lý dữ liệu song song (sơ đồ DAG, dòng sự kiện) và các biểu đồ khảo
      sát dữ liệu. Trong lúc chờ, hãy chạy <code>python run_pipeline.py</code> từ terminal.
    </ComingSoon>
  );
}
