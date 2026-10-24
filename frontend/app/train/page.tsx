import { ComingSoon } from "@/components/ComingSoon";

export default function TrainPage() {
  return (
    <ComingSoon title="Tab Huấn luyện & Đánh giá đang được xây dựng">
      Để có mô hình cho tab Suy luận, hãy chạy lần lượt <code>python run_pipeline.py</code>,{" "}
      <code>python src/tune_models.py</code> và <code>python src/evaluate.py</code>, rồi tải lại trang Suy luận.
    </ComingSoon>
  );
}
