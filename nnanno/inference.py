# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/03_inference.ipynb (unless otherwise specified).

__all__ = ['nnPredict']

# Cell
import ijson
import pkg_resources
import pandas as pd
from cytoolz import itertoolz
from tqdm.notebook import tqdm

# Cell
from typing import (
    Any,
    Optional,
    Union,
    Dict,
    List,
    Tuple,
    Set,
    Iterable,
)
from PIL import Image
import PIL

# Cell
def _filter_replace_none_image(results:List[Optional[PIL.Image.Image]]):
    fakeim = Image.fromarray(244 * np.ones((250,250,3), np.uint8))
    results = L(results)
    none_image_index = results.argwhere(lambda x: x is None) # Gets the index for images which are none
    results[none_image_index] = fakeim # Replaces None with fakeim
    return results.items, none_image_index

# Cell
class nnPredict:
    def __init__(self, learner, tyr_gpu=True):
        self.learner = learner
        self.learner.model
        self.population = pd.read_csv(pkg_resources.resource_stream('nnanno', 'data/all_year_counts.csv'),
                                      index_col=0)
    def _get_year_sample_size(self, kind,year):
        return self.population[f"{kind}_count"][year]

    def predict_from_sample_df(self, sample_df,bs=16):
        # TODO docstring
        self.sample_df = sample_df
       # Path(out_dir).mkdir(exist_ok=True)
        self.sample_df['iiif_url'] = self.sample_df.apply(lambda x: iiif_df_apply(x,size=(250,250)),axis=1)
        dfs = []
        splits = round(len(self.sample_df)/bs)
        for df in tqdm(np.array_split(sample_df, splits)):
            futures=[]
            for url in df['iiif_url'].to_list():
                with ThreadPoolExecutor() as e:
                    future = e.submit(load_url_image,url)
                    futures.append(future)
            results = [future.result() for future in futures]
            image_list, none_index = _filter_replace_none_image(results)
            im_as_arrays = [np.array(image) for image in image_list]
            if len(none_index) >0:
                        tqdm.write(f"{none_index} skipped")
            else:
                pass
            test_data = self.learner.dls.test_dl(im_as_arrays)
            with self.learner.no_bar():
                pred_tuple = self.learner.get_preds(dl=test_data, with_decoded=True)
            pred_decoded = L(pred_tuple[2], use_list=True)
            pred_tensor =  L(pred_tuple[0],use_list=None)
            pred_decoded[none_index] = np.nan; pred_tensor[none_index] = np.nan
            df["pred_decoded"] = pred_decoded.items
            df["pred_decoded"] = df['pred_decoded'].astype(float)
            # create an empty df column for each class in dls.vocab
            for c in dls.vocab:
                df[f'{c}_prob'] = ''
            # append the tensor predictions to the last `c` colomns of the df
            df.iloc[:,-dls.c:] = np.hsplit(pred_tensor.numpy(),dls.c) #split into columns
            #df.to_csv('test.csv', header=None, index=None, mode="a")
            dfs.append(df)
        return dfs



    def predict(
        self,
        kind: str,
        out_dir: str,
        bs: int = 32,
        sample_size: Union[int, float] = None,
        start_year: int = 1850,
        end_year: int = 1950,
        step: int = 1,
        year_sample:bool=True,
    ):
#         if Path(out_dir).exists() and len(os.scandir(out_dir)) >=1:
#             raise ValueError(f'{out_fn} already exists and is not empty')
        Path(out_dir).mkdir(exist_ok=True)
#         if sample_size and not year_sample:
#             if not type(sample_size) == int:
#                 raise ValueError(
#                     f"type{sample_size} is not an int. Fractions are only supported for sampling by year"
#                 )
#             sample_size = calc_year_from_total(sample_size, start_year, end_year, step)

        years = range(start_year, end_year + 1, step)
        total = self._get_year_sample_size(kind,years).sum()
        pbar = tqdm(years,total=total)
        for year in pbar:
            out_fn = _create_year_csv(out_dir,year,kind, dls)
            pbar.set_description(f"Predicting: {year}, total progress")
            if kind == ('ads' and int(year) >=1870) or (kind == 'headlines'):
                s = create_session()
            else:
                s = create_cached_session()
            with s.get(get_json_url(year, kind), timeout=60) as r:
                if r.from_cache:
                    tqdm.write('using cache')
                data = ijson.items(r.content, "item")
                # TODO add sample approach
                batches = itertoolz.partition_all(bs, iter(data))
                year_total = self._get_year_sample_size(kind,year)
                for i,batch in enumerate(tqdm(
                    batches, total=round(year_total//bs),leave=False, desc='Batch Progress')):
                    df = pd.DataFrame(batch)
                    df["iiif_url"] = df.apply(lambda x: iif_df_apply(x), axis=1)
                    futures = []
                    workers = get_max_workers(df)
                    for iif_url in df["iiif_url"].values:
                        with concurrent.futures.ThreadPoolExecutor(workers) as e:
                            future = e.submit(load_url_image, iif_url)
                            futures.append(future)
                    results = [future.result() for future in futures]
                    image_list, none_index = _filter_replace_none_image(results)
                    im_as_arrays = [np.array(image) for image in image_list]
                    if len(none_index) >0:
                        tqdm.write(f"{none_index} skipped")
                    else:
                        pass
                    test_data = learn.dls.test_dl(im_as_arrays)
                    with self.learner.no_bar():
                        pred_tuple = self.learner.get_preds(dl=test_data, with_decoded=True)
                    pred_decoded = L(pred_tuple[2], use_list=True)
                    pred_tensor =  L(pred_tuple[0],use_list=None)
                    pred_decoded[none_index] = np.nan; pred_tensor[none_index] = np.nan
                    df["pred_decoded"] = pred_decoded.items
                    df["pred_decoded"] = df['pred_decoded'].astype(float)
                    # create an empty df column for each class in dls.vocab
                    for c in dls.vocab:
                        df[f'{c}_prob'] = ''
                    # append the tensor predictions to the last `c` colomns of the df
                    df.iloc[:,-dls.c:] = np.hsplit(pred_tensor.numpy(),dls.c) #split into columns
                    df.to_csv(out_fn, header=None, index=None, mode="a")
                    pbar.update(bs)