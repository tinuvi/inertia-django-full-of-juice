import { Link, usePage } from "@inertiajs/react";

type Player = {
	name: string;
	position: string;
	number: number;
	salary: string;
	joined_at: string;
};

type Props = {
	players: Player[];
};

export default function Roster() {
	const { props } = usePage<Props>();

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Roster</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<table>
				<thead>
					<tr>
						<th>#</th>
						<th>Name</th>
						<th>Position</th>
						<th>Salary</th>
						<th>Joined</th>
					</tr>
				</thead>
				<tbody>
					{props.players.map((player) => (
						<tr key={player.number}>
							<td>{player.number}</td>
							<td>{player.name}</td>
							<td>{player.position}</td>
							<td>{player.salary}</td>
							<td>{player.joined_at}</td>
						</tr>
					))}
				</tbody>
			</table>
		</main>
	);
}
