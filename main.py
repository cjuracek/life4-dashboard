import click

from life4.ddr import DDRDataset
from life4.rank_requirements.a20_plus import pearl_1


@click.command()
@click.option("--data-path", required=True, type=str, help="Path to data file")
def main(data_path: str):
    data = DDRDataset(data_path)
    pearl_1.visualize(data)


if __name__ == "__main__":
    main()
