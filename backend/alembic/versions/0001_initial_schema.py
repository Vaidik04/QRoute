"""Initial Schema - Core Tables

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-23 08:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='operator'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # 2. vehicles
    op.create_table(
        'vehicles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('plate_number', sa.String(length=50), nullable=False),
        sa.Column('vehicle_type', sa.String(length=50), nullable=False, server_default='truck'),
        sa.Column('capacity_weight', sa.Float(), nullable=False, server_default='1000.0'),
        sa.Column('capacity_volume', sa.Float(), nullable=False, server_default='10.0'),
        sa.Column('current_lat', sa.Float(), nullable=True),
        sa.Column('current_lng', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='IDLE'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plate_number')
    )

    # 3. customers
    op.create_table(
        'customers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('time_window_start', sa.String(length=10), nullable=True),
        sa.Column('time_window_end', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. deliveries
    op.create_table(
        'deliveries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=False),
        sa.Column('package_weight', sa.Float(), nullable=False, server_default='10.0'),
        sa.Column('package_volume', sa.Float(), nullable=False, server_default='0.1'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. road_nodes
    op.create_table(
        'road_nodes',
        sa.Column('internal_node_id', sa.String(length=100), nullable=False),
        sa.Column('osm_node_id', sa.String(length=100), nullable=True),
        sa.Column('sumo_node_id', sa.String(length=100), nullable=True),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.PrimaryKeyConstraint('internal_node_id')
    )

    # 6. road_edges
    op.create_table(
        'road_edges',
        sa.Column('internal_edge_id', sa.String(length=100), nullable=False),
        sa.Column('osm_way_id', sa.String(length=100), nullable=True),
        sa.Column('sumo_edge_id', sa.String(length=100), nullable=True),
        sa.Column('source_node_id', sa.String(length=100), nullable=False),
        sa.Column('target_node_id', sa.String(length=100), nullable=False),
        sa.Column('length_meters', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('speed_limit_kph', sa.Float(), nullable=False, server_default='50.0'),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='LINESTRING', srid=4326), nullable=True),
        sa.ForeignKeyConstraint(['source_node_id'], ['road_nodes.internal_node_id'], ),
        sa.ForeignKeyConstraint(['target_node_id'], ['road_nodes.internal_node_id'], ),
        sa.PrimaryKeyConstraint('internal_edge_id')
    )

    # 7. traffic_states
    op.create_table(
        'traffic_states',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('internal_edge_id', sa.String(length=100), nullable=False),
        sa.Column('current_speed_kph', sa.Float(), nullable=False),
        sa.Column('congestion_factor', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('jam_length_meters', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['internal_edge_id'], ['road_edges.internal_edge_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. traffic_predictions
    op.create_table(
        'traffic_predictions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('internal_edge_id', sa.String(length=100), nullable=False),
        sa.Column('predicted_speed_kph', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.85'),
        sa.Column('prediction_time', sa.DateTime(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['internal_edge_id'], ['road_edges.internal_edge_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. incidents
    op.create_table(
        'incidents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('incident_type', sa.String(length=50), nullable=False, server_default='ACCIDENT'),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('reported_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. incident_edges
    op.create_table(
        'incident_edges',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('incident_id', sa.String(length=36), nullable=False),
        sa.Column('internal_edge_id', sa.String(length=100), nullable=False),
        sa.Column('impact_factor', sa.Float(), nullable=False, server_default='0.1'),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
        sa.ForeignKeyConstraint(['internal_edge_id'], ['road_edges.internal_edge_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 11. trips
    op.create_table(
        'trips',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('vehicle_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PLANNED'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 12. routes
    op.create_table(
        'routes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('trip_id', sa.String(length=36), nullable=False),
        sa.Column('total_distance_meters', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('route_geometry_geojson', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 13. route_segments
    op.create_table(
        'route_segments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('route_id', sa.String(length=36), nullable=False),
        sa.Column('internal_edge_id', sa.String(length=100), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('expected_travel_time_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['internal_edge_id'], ['road_edges.internal_edge_id'], ),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 14. optimization_runs
    op.create_table(
        'optimization_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='QUEUED'),
        sa.Column('algorithm_name', sa.String(length=50), nullable=False, server_default='D-QPSO'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 15. optimization_solutions
    op.create_table(
        'optimization_solutions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('vehicle_id', sa.String(length=36), nullable=False),
        sa.Column('customer_sequence_json', sa.Text(), nullable=False),
        sa.Column('total_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_distance', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['run_id'], ['optimization_runs.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 16. optimization_metrics
    op.create_table(
        'optimization_metrics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('total_runtime_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_distance', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('fleet_utilization', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['run_id'], ['optimization_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id')
    )

    # 17. optimization_iterations
    op.create_table(
        'optimization_iterations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('iteration_number', sa.Integer(), nullable=False),
        sa.Column('best_cost', sa.Float(), nullable=False),
        sa.Column('average_cost', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['optimization_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 18. simulation_runs
    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('sumo_config_path', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='STOPPED'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('stopped_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 19. simulation_metrics
    op.create_table(
        'simulation_metrics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('simulation_id', sa.String(length=36), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('active_vehicles', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_speed_kph', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_emissions', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulation_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 20. benchmark_runs
    op.create_table(
        'benchmark_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dataset_name', sa.String(length=100), nullable=False, server_default='bhopal_core'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 21. benchmark_results
    op.create_table(
        'benchmark_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('benchmark_id', sa.String(length=36), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=False),
        sa.Column('optimized_value', sa.Float(), nullable=False),
        sa.Column('improvement_percentage', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['benchmark_id'], ['benchmark_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('benchmark_results')
    op.drop_table('benchmark_runs')
    op.drop_table('simulation_metrics')
    op.drop_table('simulation_runs')
    op.drop_table('optimization_iterations')
    op.drop_table('optimization_metrics')
    op.drop_table('optimization_solutions')
    op.drop_table('optimization_runs')
    op.drop_table('route_segments')
    op.drop_table('routes')
    op.drop_table('trips')
    op.drop_table('incident_edges')
    op.drop_table('incidents')
    op.drop_table('traffic_predictions')
    op.drop_table('traffic_states')
    op.drop_table('road_edges')
    op.drop_table('road_nodes')
    op.drop_table('deliveries')
    op.drop_table('customers')
    op.drop_table('vehicles')
    op.drop_table('users')
