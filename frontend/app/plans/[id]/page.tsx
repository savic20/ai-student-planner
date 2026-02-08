export default function PlanDetailPage({ params }: { params: { id: string } }) {
  return (
    <div>
      <h1>Plan {params.id}</h1>
    </div>
  )
}
