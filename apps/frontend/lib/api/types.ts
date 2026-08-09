import type { components } from "./schema";

export type Schemas = components["schemas"];

export type User = Schemas["UserResponse"];
export type Restaurant = Schemas["RestaurantResponse"];
export type RestaurantList = Schemas["RestaurantListResponse"];
export type LocationItem = Schemas["LocationResponse"];
export type LocationList = Schemas["LocationListResponse"];
export type Sale = Schemas["SaleResponse"];
export type SalesList = Schemas["SalesListResponse"];
export type SalesImport = Schemas["SalesImportResponse"];
export type SalesSummary = Schemas["SalesSummaryResponse"];
export type SalesDailyPoint = Schemas["SalesDailyPoint"];
export type SalesDaily = Schemas["SalesDailyResponse"];
export type LatestForecast = Schemas["LatestForecastResponse"];
export type GenerateForecast = Schemas["GenerateForecastResponse"];
export type ForecastDay = Schemas["ForecastDay"];
export type ForecastDayItem = Schemas["ForecastDayItem"];
export type ForecastAccuracy = Schemas["ForecastAccuracyResponse"];
export type Backtest = Schemas["BacktestResponse"];
export type ModelEvaluationRun = Schemas["ModelEvaluationRunResponse"];
export type PerItemEvaluation = Schemas["PerItemEvaluationResponse"];

export type MenuItem = Schemas["MenuItem"];
export type MenuItemList = Schemas["MenuItemListResponse"];
export type Ingredient = Schemas["IngredientResponse"];
export type IngredientList = Schemas["IngredientListResponse"];
export type Recipe = Schemas["RecipeResponse"];
export type RecipeLine = Schemas["RecipeLineResponse"];
export type IngredientDemand = Schemas["IngredientDemandResponse"];
export type IngredientDemandDay = Schemas["IngredientDemandDay"];
export type IngredientQuantity = Schemas["IngredientQuantitySchema"];
export type PrepSheet = Schemas["PrepSheetResponse"];
export type PrepSheetItem = Schemas["PrepSheetItem"];

export type ApiErrorDetail = {
  row?: number | null;
  field?: string | null;
  message: string;
};
