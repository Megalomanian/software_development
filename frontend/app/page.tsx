import Link from "next/link";
import {
  BarChart3,
  Database,
  FlaskConical,
  Rocket,
  Activity,
} from "lucide-react";

const cards = [
  { title: "数据管理", desc: "上传数据、自动画像、版本管理", href: "/data", icon: Database },
  { title: "实验训练", desc: "可视化 Pipeline、实验对比", href: "/experiments", icon: FlaskConical },
  { title: "模型管理", desc: "注册中心、版本管理、评估", href: "/models", icon: BarChart3 },
  { title: "在线推理", desc: "一键部署、弹性伸缩", href: "/deployments", icon: Rocket },
  { title: "监控告警", desc: "延迟/吞吐/漂移检测", href: "/monitoring", icon: Activity },
];

export default function Home() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">ML Platform</h1>
      <p className="text-gray-500 mb-8">低代码 MLOps，从数据到推理一步到位</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map(({ title, desc, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="block p-6 bg-white rounded-xl border hover:shadow-md transition-shadow"
          >
            <Icon className="w-8 h-8 text-blue-600 mb-3" />
            <h3 className="text-lg font-semibold mb-1">{title}</h3>
            <p className="text-sm text-gray-500">{desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
